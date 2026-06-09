"""
Pydantic v2 request/response schemas for the loans API.

Request schemas:
    CheckoutRequest — copy_id and user_id to check out a copy to a student

Response schemas (from_attributes=True — instantiated from ORM Loan rows):
    StudentBriefResponse — nested student info in loan responses
    BookBriefResponse    — nested book info in loan responses
    CopyBriefResponse    — nested copy info in loan responses
    LoanResponse         — single loan with is_overdue computed field
    LoansListResponse    — paginated list of loans
"""
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, computed_field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CheckoutRequest(BaseModel):
    """Fields required to check out a copy to a student."""
    copy_id: int
    user_id: int


# ---------------------------------------------------------------------------
# Nested response schemas
# ---------------------------------------------------------------------------


class StudentBriefResponse(BaseModel):
    """Brief student info embedded in loan responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None


class BookBriefResponse(BaseModel):
    """Brief book info embedded in loan responses (from copy.book)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str


class CopyBriefResponse(BaseModel):
    """Brief copy info embedded in loan responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    barcode: str | None


# ---------------------------------------------------------------------------
# Loan response schema
# ---------------------------------------------------------------------------


class LoanResponse(BaseModel):
    """
    Full loan response — returned after checkout, return, and in list endpoints.

    is_overdue is a computed field: True when due_date < now(UTC) AND returned_at is None.
    This is always recomputed at serialization time — no stored status column.
    (CONTEXT D-01: overdue computed at query time, no background job needed in Phase 3.)
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    copy_id: int
    copy: CopyBriefResponse
    book: BookBriefResponse
    borrower: StudentBriefResponse
    checked_out_at: datetime
    due_date: datetime
    returned_at: datetime | None

    @computed_field  # type: ignore[misc]
    @property
    def is_overdue(self) -> bool:
        return self.due_date < datetime.now(timezone.utc) and self.returned_at is None


# ---------------------------------------------------------------------------
# List response schema
# ---------------------------------------------------------------------------


class LoansListResponse(BaseModel):
    """Paginated list of loans."""
    items: list[LoanResponse]
    total: int
