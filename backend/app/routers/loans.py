"""
Loans router — circulation endpoints for checkout, return, and loan queries.

Router architecture (PITFALLS C4 — RBAC at router level):
    loans_router         — POST /api/librarian/loans/checkout
                           PATCH /api/librarian/loans/{loan_id}/return
                           GET   /api/librarian/loans
                           Requires: librarian role

    student_loans_router — GET /api/loans/my
                           Requires: authenticated user (any role)
                           user_id sourced from JWT sub (T-03-01)

Threat model compliance:
    T-03-01  GET /api/loans/my user_id from get_current_user (JWT sub), never from request
    T-03-02  PATCH return: idempotency check — 409 if already returned
    T-03-03  POST checkout: role check before checkout — 400 if not student
"""
import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.enums import CopyStatus, UserRole
from app.dependencies import get_current_user, require_librarian
from app.models.copy import Copy
from app.models.fine import Fine
from app.models.library_settings import LibrarySettings
from app.models.loan import Loan
from app.models.user import User
from app.schemas.loans import CheckoutRequest, LoanResponse, LoansListResponse

# ---------------------------------------------------------------------------
# Router definitions
# ---------------------------------------------------------------------------

loans_router = APIRouter(
    prefix="/librarian/loans",
    tags=["loans-librarian"],
    dependencies=[Depends(require_librarian)],
)

student_loans_router = APIRouter(
    prefix="/loans",
    tags=["loans-student"],
)


# ---------------------------------------------------------------------------
# Helper — eager-load a single loan's relationships for response
# ---------------------------------------------------------------------------

LOAN_EAGER_OPTIONS = [
    selectinload(Loan.copy).selectinload(Copy.book),
    selectinload(Loan.borrower),
]


def _loan_to_response(loan: Loan) -> LoanResponse:
    """
    Build a LoanResponse from an ORM Loan with eager-loaded relationships.

    The LoanResponse.book field comes from loan.copy.book — map it here so
    Pydantic's from_attributes mode can find it as a direct attribute.
    """
    # Attach book directly to the loan instance so LoanResponse can read it
    loan.book = loan.copy.book  # type: ignore[attr-defined]
    return LoanResponse.model_validate(loan)


# ===========================================================================
# loans_router — librarian endpoints
# ===========================================================================


@loans_router.post(
    "/checkout",
    response_model=LoanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def checkout_copy(
    data: CheckoutRequest,
    session: AsyncSession = Depends(get_db),
) -> LoanResponse:
    """
    Check out a copy to a student.

    POST /api/librarian/loans/checkout

    Validates:
    - Copy exists and status == available (409 if not — T-03-02, D-05)
    - User exists and role == student (400 if not — T-03-03, D-05)
    - Calculates due_date = now() + loan_period_days from library_settings (D-04)
    """
    # 1. Load copy
    copy_result = await session.execute(select(Copy).where(Copy.id == data.copy_id))
    copy = copy_result.scalar_one_or_none()
    if copy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copy not found")

    # 2. Check availability (T-03-02, D-05)
    if copy.status != CopyStatus.available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Copy is not available for checkout",
        )

    # 3. Load user
    user_result = await session.execute(select(User).where(User.id == data.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 4. Check student role (T-03-03, D-05)
    if user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only check out to student accounts",
        )

    # 5. Load library settings for loan_period_days (D-04 — never hardcoded)
    settings_result = await session.execute(
        select(LibrarySettings).where(LibrarySettings.id == 1)
    )
    library_settings = settings_result.scalar_one_or_none()
    loan_period_days = library_settings.loan_period_days if library_settings else 14

    # 6. Calculate due_date
    due_date = datetime.now(timezone.utc) + timedelta(days=loan_period_days)

    # 7. Create loan and update copy status
    loan = Loan(copy_id=data.copy_id, user_id=data.user_id, due_date=due_date)
    copy.status = CopyStatus.on_loan
    session.add(loan)
    await session.flush()  # get loan.id before eager-loading

    # 8. Reload loan with eager-loaded relationships for response
    loan_result = await session.execute(
        select(Loan).where(Loan.id == loan.id).options(*LOAN_EAGER_OPTIONS)
    )
    loan_with_relations = loan_result.scalar_one()
    await session.commit()

    return _loan_to_response(loan_with_relations)


@loans_router.patch(
    "/{loan_id}/return",
    response_model=LoanResponse,
)
async def return_loan(
    loan_id: int,
    session: AsyncSession = Depends(get_db),
) -> LoanResponse:
    """
    Process a book return.

    PATCH /api/librarian/loans/{loan_id}/return

    Sets loan.returned_at = now() and copy.status = available.
    Returns 409 if the loan is already returned (idempotency — T-03-02).
    """
    # 1. Load loan
    loan_result = await session.execute(
        select(Loan).where(Loan.id == loan_id).options(*LOAN_EAGER_OPTIONS)
    )
    loan = loan_result.scalar_one_or_none()
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    # 2. Idempotency check (T-03-02)
    if loan.returned_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Loan already returned",
        )

    # 3. Mark returned and restore copy availability
    loan.returned_at = datetime.now(timezone.utc)

    copy_result = await session.execute(select(Copy).where(Copy.id == loan.copy_id))
    copy = copy_result.scalar_one_or_none()
    if copy is not None:
        copy.status = CopyStatus.available

    # 4. Auto-calculate fine for overdue returns (FINE-01, T-04-01 mitigated)
    # days_overdue is computed from DB timestamps — no client input into fine amount.
    if loan.returned_at > loan.due_date:
        days_overdue = math.ceil(
            (loan.returned_at - loan.due_date).total_seconds() / 86400
        )
    else:
        days_overdue = 0

    if days_overdue > 0:
        # Load fine rate from library_settings; fall back to $0.25 if no settings row
        settings_result = await session.execute(
            select(LibrarySettings).where(LibrarySettings.id == 1)
        )
        library_settings = settings_result.scalar_one_or_none()
        fine_rate = (
            Decimal(str(library_settings.fine_rate_per_day))
            if library_settings
            else Decimal("0.25")
        )
        fine = Fine(
            loan_id=loan.id,
            amount=fine_rate * days_overdue,
            days_overdue=days_overdue,
        )
        session.add(fine)

    await session.flush()

    # 5. Reload with fresh relationships for response
    loan_result = await session.execute(
        select(Loan).where(Loan.id == loan_id).options(*LOAN_EAGER_OPTIONS)
    )
    loan_refreshed = loan_result.scalar_one()
    await session.commit()

    return _loan_to_response(loan_refreshed)


@loans_router.get(
    "",
    response_model=LoansListResponse,
)
async def list_loans(
    overdue: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> LoansListResponse:
    """
    List active loans (returned_at IS NULL).

    GET /api/librarian/loans?overdue=true&page=1&page_size=20

    overdue=true: also filter where due_date < now() (D-01 — computed at query time).
    No stored overdue status column; no background job needed in Phase 3.
    """
    now = datetime.now(timezone.utc)

    # Base filter: active loans only (not returned)
    base_filter = [Loan.returned_at.is_(None)]
    if overdue:
        base_filter.append(Loan.due_date < now)

    # Count total
    count_result = await session.execute(
        select(func.count(Loan.id)).where(*base_filter)
    )
    total: int = count_result.scalar_one()

    # Paginated loans with eager-loaded relationships
    loans_result = await session.execute(
        select(Loan)
        .where(*base_filter)
        .options(*LOAN_EAGER_OPTIONS)
        .order_by(Loan.due_date)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    loans = loans_result.scalars().all()

    return LoansListResponse(
        items=[_loan_to_response(loan) for loan in loans],
        total=total,
    )


# ===========================================================================
# student_loans_router — student endpoints
# ===========================================================================


@student_loans_router.get(
    "/my",
    response_model=LoansListResponse,
)
async def get_my_loans(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LoansListResponse:
    """
    Get the current student's active loans.

    GET /api/loans/my

    user_id always sourced from JWT sub via get_current_user — never from
    query params or request body (T-03-01).
    """
    loans_result = await session.execute(
        select(Loan)
        .where(Loan.user_id == current_user.id, Loan.returned_at.is_(None))
        .options(
            selectinload(Loan.copy).selectinload(Copy.book),
            selectinload(Loan.borrower),
        )
        .order_by(Loan.due_date)
    )
    loans = loans_result.scalars().all()

    return LoansListResponse(
        items=[_loan_to_response(loan) for loan in loans],
        total=len(loans),
    )
