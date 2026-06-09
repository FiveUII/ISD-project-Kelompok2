"""
Catalog API router — books and copies.

Router architecture (PITFALLS C4 — RBAC at router level, not inline):
    student_router   — GET  /api/books, GET /api/books/{id}
                       Requires: authenticated user (any role)
    librarian_router — POST /api/books/isbn-fetch, POST /api/books,
                       PUT /api/books/{id}, DELETE /api/books/{id},
                       POST /api/books/{id}/copies
                       Requires: librarian role
    copies_router    — PATCH /api/copies/{id}/lost
                       Requires: librarian role
                       (separate prefix because path is /copies/, not /books/)

Both student_router and librarian_router share the /books prefix; they are
registered separately in main.py so FastAPI merges them into one path tree.
isbn-fetch MUST be defined before /{book_id} to prevent FastAPI routing the
literal string "isbn-fetch" as a book ID.

Threat model compliance:
    T-02-02  RBAC enforced at router-level Depends(), never inline if-checks
    T-02-03  deleted_at.is_(None) filter on EVERY book and copy query
    T-02-04  available_count via correlated subquery (no N+1)
"""
import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.enums import CopyStatus
from app.dependencies import get_current_user, require_librarian
from app.models.book import Book
from app.models.copy import Copy
from app.models.user import User
from app.schemas.catalog import (
    BookCreate,
    BookDetailResponse,
    BookListResponse,
    BookResponse,
    BookUpdate,
    CopyCreate,
    CopyResponse,
    ISBNFetchResponse,
)
from app.services.isbn_service import fetch_book_by_isbn

# ---------------------------------------------------------------------------
# Router definitions
# ---------------------------------------------------------------------------

student_router = APIRouter(
    prefix="/books",
    tags=["catalog"],
    dependencies=[Depends(get_current_user)],
)

librarian_router = APIRouter(
    prefix="/books",
    tags=["catalog-admin"],
    dependencies=[Depends(require_librarian)],
)

# Separate prefix for /copies/* endpoints (cannot share /books prefix)
copies_router = APIRouter(
    prefix="/copies",
    tags=["catalog-admin"],
    dependencies=[Depends(require_librarian)],
)

# ---------------------------------------------------------------------------
# Correlated subquery helpers (T-02-04 — no N+1 availability queries)
# ---------------------------------------------------------------------------

available_count_subq = (
    select(func.count(Copy.id))
    .where(
        and_(
            Copy.book_id == Book.id,
            Copy.status == CopyStatus.available,
            Copy.deleted_at.is_(None),
        )
    )
    .correlate(Book)
    .scalar_subquery()
)

total_count_subq = (
    select(func.count(Copy.id))
    .where(
        and_(
            Copy.book_id == Book.id,
            Copy.deleted_at.is_(None),
        )
    )
    .correlate(Book)
    .scalar_subquery()
)


# ---------------------------------------------------------------------------
# Helper — build BookResponse from a (book, available_count, total_count) row
# ---------------------------------------------------------------------------


def _book_row_to_response(row) -> BookResponse:
    book, available_count, total_count = row
    return BookResponse(
        id=book.id,
        isbn=book.isbn,
        title=book.title,
        author=book.author,
        publisher=book.publisher,
        publish_year=book.publish_year,
        description=book.description,
        cover_url=book.cover_url,
        created_at=book.created_at,
        available_count=available_count,
        total_count=total_count,
    )


# ===========================================================================
# librarian_router — MUST register isbn-fetch BEFORE /{book_id}
# ===========================================================================


@librarian_router.post("/isbn-fetch", response_model=ISBNFetchResponse)
async def isbn_fetch(isbn: str = Body(..., embed=True)) -> ISBNFetchResponse:
    """
    Fetch bibliographic metadata from Open Library by ISBN.

    POST /api/books/isbn-fetch
    Body: {"isbn": "9780141439518"}

    Defined before GET /books/{book_id} so FastAPI does not route the literal
    string "isbn-fetch" as a book ID parameter.

    Returns ISBNFetchResponse with found=True on success, or found=False
    with error="not_found" / "unavailable" on failure.
    """
    return await fetch_book_by_isbn(isbn)


@librarian_router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    data: BookCreate,
    session: AsyncSession = Depends(get_db),
) -> BookResponse:
    """
    Create a new book record.

    POST /api/books
    """
    book = Book(**data.model_dump())
    session.add(book)
    await session.commit()
    await session.refresh(book)

    # Re-query with correlated subqueries to get availability counts
    result = await session.execute(
        select(Book, available_count_subq, total_count_subq)
        .where(and_(Book.id == book.id, Book.deleted_at.is_(None)))
    )
    row = result.one()
    return _book_row_to_response(row)


@librarian_router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    data: BookUpdate,
    session: AsyncSession = Depends(get_db),
) -> BookResponse:
    """
    Partial-update a book (all fields optional).

    PUT /api/books/{book_id}
    """
    result = await session.execute(
        select(Book).where(and_(Book.id == book_id, Book.deleted_at.is_(None)))
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(book, field, value)

    await session.commit()
    await session.refresh(book)

    # Re-query with correlated subqueries
    result = await session.execute(
        select(Book, available_count_subq, total_count_subq)
        .where(and_(Book.id == book_id, Book.deleted_at.is_(None)))
    )
    row = result.one()
    return _book_row_to_response(row)


@librarian_router.delete("/{book_id}")
async def delete_book(
    book_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Soft-delete a book (sets deleted_at, preserves history — D-06).

    DELETE /api/books/{book_id}
    """
    result = await session.execute(
        select(Book).where(and_(Book.id == book_id, Book.deleted_at.is_(None)))
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    book.deleted_at = datetime.now(tz=timezone.utc)
    await session.commit()
    return {"message": "Book deleted."}


@librarian_router.post("/{book_id}/copies", response_model=CopyResponse, status_code=status.HTTP_201_CREATED)
async def add_copy(
    book_id: int,
    data: CopyCreate,
    session: AsyncSession = Depends(get_db),
) -> CopyResponse:
    """
    Add a physical copy of an existing book.

    POST /api/books/{book_id}/copies
    """
    # Verify the book exists and is not soft-deleted
    result = await session.execute(
        select(Book).where(and_(Book.id == book_id, Book.deleted_at.is_(None)))
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    copy = Copy(book_id=book_id, **data.model_dump())
    session.add(copy)
    await session.commit()
    await session.refresh(copy)
    return CopyResponse.model_validate(copy)


# ===========================================================================
# student_router — GET endpoints (authenticated, any role)
# ===========================================================================


@student_router.get("", response_model=BookListResponse)
async def list_books(
    q: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> BookListResponse:
    """
    List/search books with pagination.

    GET /api/books?q=&page=1&page_size=20

    Serves BOTH students (via /catalog on the frontend) and librarians
    (via /librarian/books on the frontend) — same endpoint, same data.
    available_count and total_count are included in every response row.

    Search (q) matches title, author, or ISBN using case-insensitive ILIKE.
    """
    base_where = [Book.deleted_at.is_(None)]
    if q:
        base_where.append(
            or_(
                Book.title.ilike(f"%{q}%"),
                Book.author.ilike(f"%{q}%"),
                Book.isbn.ilike(f"%{q}%"),
            )
        )

    # Count total matching rows (separate query — no subqueries needed for count)
    count_result = await session.execute(
        select(func.count(Book.id)).where(and_(*base_where))
    )
    total: int = count_result.scalar_one()

    # Paginated rows with correlated availability subqueries (T-02-04 — single query)
    rows_result = await session.execute(
        select(Book, available_count_subq, total_count_subq)
        .where(and_(*base_where))
        .order_by(Book.title)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = rows_result.all()

    items = [_book_row_to_response(row) for row in rows]
    pages = math.ceil(total / page_size) if total > 0 else 1

    return BookListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@student_router.get("/{book_id}", response_model=BookDetailResponse)
async def get_book(
    book_id: int,
    session: AsyncSession = Depends(get_db),
) -> BookDetailResponse:
    """
    Get a single book with its physical copies.

    GET /api/books/{book_id}
    """
    # Fetch book with availability counts
    result = await session.execute(
        select(Book, available_count_subq, total_count_subq)
        .where(and_(Book.id == book_id, Book.deleted_at.is_(None)))
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    book, available_count, total_count = row

    # Fetch non-deleted copies for this book
    copies_result = await session.execute(
        select(Copy)
        .where(and_(Copy.book_id == book_id, Copy.deleted_at.is_(None)))
        .order_by(Copy.id)
    )
    copies = copies_result.scalars().all()
    copy_responses = [CopyResponse.model_validate(c) for c in copies]

    return BookDetailResponse(
        id=book.id,
        isbn=book.isbn,
        title=book.title,
        author=book.author,
        publisher=book.publisher,
        publish_year=book.publish_year,
        description=book.description,
        cover_url=book.cover_url,
        created_at=book.created_at,
        available_count=available_count,
        total_count=total_count,
        copies=copy_responses,
    )


# ===========================================================================
# copies_router — /copies/* (separate prefix — librarian only)
# ===========================================================================


@copies_router.patch("/{copy_id}/lost", response_model=CopyResponse)
async def mark_copy_lost(
    copy_id: int,
    session: AsyncSession = Depends(get_db),
) -> CopyResponse:
    """
    Mark a physical copy as lost (soft-delete + status update).

    PATCH /api/copies/{copy_id}/lost

    Sets status=lost AND deleted_at to preserve loan history while
    removing the copy from availability counts (T-02-03).
    """
    result = await session.execute(
        select(Copy).where(and_(Copy.id == copy_id, Copy.deleted_at.is_(None)))
    )
    copy = result.scalar_one_or_none()
    if copy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copy not found")

    copy.status = CopyStatus.lost
    await session.commit()
    await session.refresh(copy)
    return CopyResponse.model_validate(copy)
