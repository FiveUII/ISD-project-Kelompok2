"""
Pydantic v2 request/response schemas for the catalog API.

Request schemas (no from_attributes — no ORM mapping needed):
    BookCreate, BookUpdate, CopyCreate

Response schemas (with from_attributes=True — instantiated from ORM rows or row tuples):
    CopyResponse, BookResponse, BookDetailResponse, BookListResponse, ISBNFetchResponse
"""
import math
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import CopyCondition, CopyStatus


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class BookCreate(BaseModel):
    """Fields required/optional to create a new book record."""
    isbn: Optional[str] = None
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    publisher: Optional[str] = None
    publish_year: Optional[int] = Field(None, ge=1000, le=2100)
    description: Optional[str] = None
    cover_url: Optional[str] = None


class BookUpdate(BaseModel):
    """All fields optional — supports partial (PATCH-style) PUT updates."""
    isbn: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    publisher: Optional[str] = None
    publish_year: Optional[int] = Field(None, ge=1000, le=2100)
    description: Optional[str] = None
    cover_url: Optional[str] = None


class CopyCreate(BaseModel):
    """Fields to add a new physical copy of a book."""
    barcode: Optional[str] = None
    condition: CopyCondition = CopyCondition.good


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class CopyResponse(BaseModel):
    """Single physical copy — returned after create or in book detail."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    barcode: Optional[str]
    condition: CopyCondition
    status: CopyStatus
    created_at: datetime


class BookResponse(BaseModel):
    """
    Book record with availability counts.

    available_count and total_count are NOT columns on the Book ORM model —
    they are populated from correlated subquery results in the router.
    Declared with default=0 so Pydantic does not raise if not supplied.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    isbn: Optional[str]
    title: str
    author: str
    publisher: Optional[str]
    publish_year: Optional[int]
    description: Optional[str]
    cover_url: Optional[str]
    created_at: datetime
    available_count: int = 0
    total_count: int = 0


class BookDetailResponse(BookResponse):
    """Book record + its physical copies. Used by GET /api/books/{id}."""
    copies: list[CopyResponse] = []


class BookListResponse(BaseModel):
    """Paginated list of books."""
    items: list[BookResponse]
    total: int
    page: int
    page_size: int
    pages: int  # math.ceil(total / page_size) — computed by router


class ISBNFetchResponse(BaseModel):
    """
    Result of the Open Library 3-step ISBN fetch.

    found=False when the ISBN is unknown (error="not_found") or the
    external API is unreachable (error="unavailable").
    """
    found: bool
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    error: Optional[str] = None  # "not_found" | "unavailable" | None
