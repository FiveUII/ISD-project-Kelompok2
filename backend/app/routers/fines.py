"""
Fines router — fine management endpoints for librarians.

Router:
    fines_router — GET /api/librarian/fines (list with loan/borrower/book info)
                   PATCH /api/librarian/fines/{fine_id}/pay   (mark paid)
                   PATCH /api/librarian/fines/{fine_id}/waive (waive with reason)
                   All require: librarian role (T-04-04 mitigated)

Threat model compliance:
    T-04-04  Router-level Depends(require_librarian) — students get 403
    T-04-05  WaiveRequest.reason validator rejects blank reasons
    T-04-06  409 guard on pay/waive when fine.status != "unpaid" (already settled)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.dependencies import require_librarian
from app.models.copy import Copy
from app.models.fine import Fine
from app.models.loan import Loan
from app.schemas.fines import (
    FineDetailResponse,
    FinesListResponse,
    WaiveRequest,
)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

fines_router = APIRouter(
    prefix="/librarian/fines",
    tags=["fines"],
    dependencies=[Depends(require_librarian)],
)

# ---------------------------------------------------------------------------
# Eager-load options for fines list
# ---------------------------------------------------------------------------

FINE_EAGER_OPTIONS = [
    selectinload(Fine.loan).selectinload(Loan.borrower),
    selectinload(Fine.loan).selectinload(Loan.copy).selectinload(Copy.book),
]


def _fine_to_detail(fine: Fine) -> FineDetailResponse:
    """
    Build a FineDetailResponse from an ORM Fine with eager-loaded relationships.

    Attaches fine.loan.book from fine.loan.copy.book so LoanBriefForFine can read
    it via from_attributes — same pattern as _loan_to_response in loans router.
    """
    fine.loan.book = fine.loan.copy.book  # type: ignore[attr-defined]
    return FineDetailResponse.model_validate(fine)


# ---------------------------------------------------------------------------
# GET /librarian/fines — list all fines
# ---------------------------------------------------------------------------


@fines_router.get("", response_model=FinesListResponse)
async def list_fines(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> FinesListResponse:
    """
    List all fines with loan/borrower/book info.

    GET /api/librarian/fines?status=unpaid&page=1&page_size=20

    status filter is optional — omit to see all fines.
    Results ordered by created_at DESC (newest first).
    """
    base_filter = []
    if status_filter:
        base_filter.append(Fine.status == status_filter)

    # Count total
    count_result = await session.execute(
        select(func.count(Fine.id)).where(*base_filter)
    )
    total: int = count_result.scalar_one()

    # Paginated fines with eager-loaded relationships
    fines_result = await session.execute(
        select(Fine)
        .where(*base_filter)
        .options(*FINE_EAGER_OPTIONS)
        .order_by(Fine.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    fines = fines_result.scalars().all()

    return FinesListResponse(
        items=[_fine_to_detail(fine) for fine in fines],
        total=total,
    )


# ---------------------------------------------------------------------------
# PATCH /librarian/fines/{fine_id}/pay — mark a fine as paid
# ---------------------------------------------------------------------------


@fines_router.patch("/{fine_id}/pay", response_model=FineDetailResponse)
async def pay_fine(
    fine_id: int,
    session: AsyncSession = Depends(get_db),
) -> FineDetailResponse:
    """
    Mark a fine as paid.

    PATCH /api/librarian/fines/{fine_id}/pay

    Returns 404 if fine not found.
    Returns 409 if fine is already paid or waived (T-04-06).
    """
    fine_result = await session.execute(
        select(Fine).where(Fine.id == fine_id).options(*FINE_EAGER_OPTIONS)
    )
    fine = fine_result.scalar_one_or_none()
    if fine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fine not found"
        )

    if fine.status != "unpaid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fine already settled",
        )

    fine.status = "paid"
    await session.commit()

    # Reload with fresh relationships for response
    fine_result = await session.execute(
        select(Fine).where(Fine.id == fine_id).options(*FINE_EAGER_OPTIONS)
    )
    fine_refreshed = fine_result.scalar_one()

    return _fine_to_detail(fine_refreshed)


# ---------------------------------------------------------------------------
# PATCH /librarian/fines/{fine_id}/waive — waive a fine with reason
# ---------------------------------------------------------------------------


@fines_router.patch("/{fine_id}/waive", response_model=FineDetailResponse)
async def waive_fine(
    fine_id: int,
    data: WaiveRequest,
    session: AsyncSession = Depends(get_db),
) -> FineDetailResponse:
    """
    Waive a fine with a reason.

    PATCH /api/librarian/fines/{fine_id}/waive
    Body: {"reason": "non-empty string"}

    Returns 404 if fine not found.
    Returns 409 if fine is already paid or waived (T-04-06).
    Returns 422 if reason is empty/whitespace (T-04-05 — WaiveRequest validator).
    """
    fine_result = await session.execute(
        select(Fine).where(Fine.id == fine_id).options(*FINE_EAGER_OPTIONS)
    )
    fine = fine_result.scalar_one_or_none()
    if fine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fine not found"
        )

    if fine.status != "unpaid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fine already settled",
        )

    fine.status = "waived"
    fine.waiver_reason = data.reason
    await session.commit()

    # Reload with fresh relationships for response
    fine_result = await session.execute(
        select(Fine).where(Fine.id == fine_id).options(*FINE_EAGER_OPTIONS)
    )
    fine_refreshed = fine_result.scalar_one()

    return _fine_to_detail(fine_refreshed)
