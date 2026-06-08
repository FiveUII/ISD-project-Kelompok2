"""
Tests for data model structure - TDD RED phase.
These tests verify Book/Copy separation, enums, soft-delete columns,
and LibrarySettings columns.
"""
import pytest
from sqlalchemy import inspect


def test_book_and_copy_are_separate_models():
    """Book and Copy must be distinct SQLAlchemy models in separate modules."""
    from app.models.book import Book
    from app.models.copy import Copy

    assert Book.__tablename__ == "books"
    assert Copy.__tablename__ == "copies"


def test_copy_has_book_id_fk():
    """Copy must have a book_id FK to Book."""
    from app.models.copy import Copy

    col_names = [c.name for c in Copy.__table__.columns]
    assert "book_id" in col_names


def test_book_has_no_availability_columns():
    """Book must NOT have available/quantity/copies_available columns (PITFALLS C1)."""
    from app.models.book import Book

    col_names = [c.name for c in Book.__table__.columns]
    assert "available" not in col_names
    assert "quantity" not in col_names
    assert "copies_available" not in col_names


def test_copy_status_uses_enum():
    """Copy.status must use CopyStatus enum with correct values."""
    from app.core.enums import CopyStatus

    assert CopyStatus.available == "available"
    assert CopyStatus.on_loan == "on_loan"
    assert CopyStatus.lost == "lost"
    assert CopyStatus.withdrawn == "withdrawn"


def test_user_role_uses_enum():
    """User.role must use UserRole enum with correct values."""
    from app.core.enums import UserRole

    assert UserRole.student == "student"
    assert UserRole.librarian == "librarian"


def test_copy_condition_enum():
    """CopyCondition enum must have correct values."""
    from app.core.enums import CopyCondition

    assert CopyCondition.good == "good"
    assert CopyCondition.fair == "fair"
    assert CopyCondition.poor == "poor"


def test_soft_delete_on_user():
    """User must have a nullable deleted_at column (soft delete, PITFALLS m2)."""
    from app.models.user import User

    col_names = [c.name for c in User.__table__.columns]
    assert "deleted_at" in col_names
    deleted_at_col = User.__table__.columns["deleted_at"]
    assert deleted_at_col.nullable is True


def test_soft_delete_on_book():
    """Book must have a nullable deleted_at column (soft delete)."""
    from app.models.book import Book

    col_names = [c.name for c in Book.__table__.columns]
    assert "deleted_at" in col_names
    deleted_at_col = Book.__table__.columns["deleted_at"]
    assert deleted_at_col.nullable is True


def test_soft_delete_on_copy():
    """Copy must have a nullable deleted_at column (soft delete)."""
    from app.models.copy import Copy

    col_names = [c.name for c in Copy.__table__.columns]
    assert "deleted_at" in col_names
    deleted_at_col = Copy.__table__.columns["deleted_at"]
    assert deleted_at_col.nullable is True


def test_library_settings_columns():
    """LibrarySettings must have loan_period_days and fine_rate_per_day columns (PITFALLS m3)."""
    from app.models.library_settings import LibrarySettings

    col_names = [c.name for c in LibrarySettings.__table__.columns]
    assert "loan_period_days" in col_names
    assert "fine_rate_per_day" in col_names
    assert "reminder_days_before" in col_names


def test_user_columns():
    """User must have expected columns."""
    from app.models.user import User

    col_names = [c.name for c in User.__table__.columns]
    assert "id" in col_names
    assert "email" in col_names
    assert "full_name" in col_names
    assert "hashed_password" in col_names
    assert "role" in col_names
    assert "is_email_verified" in col_names
    assert "created_at" in col_names


def test_book_columns():
    """Book must have expected bibliographic columns."""
    from app.models.book import Book

    col_names = [c.name for c in Book.__table__.columns]
    assert "id" in col_names
    assert "isbn" in col_names
    assert "title" in col_names
    assert "author" in col_names
    assert "publisher" in col_names
    assert "publish_year" in col_names
    assert "description" in col_names
    assert "cover_url" in col_names
    assert "created_at" in col_names


def test_copy_columns():
    """Copy must have expected columns."""
    from app.models.copy import Copy

    col_names = [c.name for c in Copy.__table__.columns]
    assert "id" in col_names
    assert "book_id" in col_names
    assert "barcode" in col_names
    assert "condition" in col_names
    assert "status" in col_names
    assert "created_at" in col_names
