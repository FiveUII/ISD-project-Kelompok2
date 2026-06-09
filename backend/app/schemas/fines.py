"""
Pydantic v2 request/response schemas for the fines API.

Request schemas:
    WaiveRequest — reason for waiving a fine (non-empty string required)

Response schemas (from_attributes=True — instantiated from ORM Fine rows):
    FineResponse       — basic fine fields
    LoanBriefForFine   — nested loan/borrower/book info for fines list
    FineDetailResponse — fine with nested loan info
    FinesListResponse  — paginated list of fines
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.loans import BookBriefResponse, StudentBriefResponse


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class WaiveRequest(BaseModel):
    """Body for waiving a fine — reason is required and must be non-empty."""
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("reason cannot be empty")
        return v.strip()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class FineResponse(BaseModel):
    """Basic fine fields returned after creation or status update."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    amount: Decimal
    days_overdue: int
    status: str
    waiver_reason: str | None
    created_at: datetime


class LoanBriefForFine(BaseModel):
    """Brief loan info embedded in FineDetailResponse — includes borrower and book."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    due_date: datetime
    returned_at: datetime | None
    borrower: StudentBriefResponse
    book: BookBriefResponse


class FineDetailResponse(BaseModel):
    """Fine with nested loan/borrower/book info for the fines management table."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    amount: Decimal
    days_overdue: int
    status: str
    waiver_reason: str | None
    created_at: datetime
    loan: LoanBriefForFine


class FinesListResponse(BaseModel):
    """Paginated list of fines with detail."""
    items: list[FineDetailResponse]
    total: int
