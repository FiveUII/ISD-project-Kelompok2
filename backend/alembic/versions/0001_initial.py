"""Initial schema: users, books, copies, library_settings

Revision ID: 0001
Revises:
Create Date: 2026-06-08

Creates all foundation tables:
- users (with UserRole enum and soft-delete)
- books (bibliographic records, NO availability columns)
- copies (physical items with CopyStatus/CopyCondition enums and soft-delete)
- library_settings (configurable loan period and fine rate)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create PostgreSQL enum types
    userrole_enum = sa.Enum("student", "librarian", name="userrole")
    copystatus_enum = sa.Enum("available", "on_loan", "lost", "withdrawn", name="copystatus")
    copycondition_enum = sa.Enum("good", "fair", "poor", name="copycondition")

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            userrole_enum,
            nullable=False,
            server_default="student",
        ),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Create books table (bibliographic records — NO availability columns per PITFALLS C1)
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("isbn", sa.String(20), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("publish_year", sa.SmallInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.String(1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_books_isbn", "books", ["isbn"], unique=True)

    # Create copies table (physical items, FK to books)
    op.create_table(
        "copies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column(
            "condition",
            copycondition_enum,
            nullable=False,
            server_default="good",
        ),
        sa.Column(
            "status",
            copystatus_enum,
            nullable=False,
            server_default="available",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_copies_book_id", "copies", ["book_id"])
    op.create_index("ix_copies_barcode", "copies", ["barcode"], unique=True)

    # Create library_settings table (configurable loan period + fine rate, PITFALLS m3)
    op.create_table(
        "library_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("loan_period_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column(
            "fine_rate_per_day",
            sa.Numeric(6, 2),
            nullable=False,
            server_default="0.25",
        ),
        sa.Column("reminder_days_before", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("library_settings")
    op.drop_index("ix_copies_barcode", table_name="copies")
    op.drop_index("ix_copies_book_id", table_name="copies")
    op.drop_table("copies")
    op.drop_index("ix_books_isbn", table_name="books")
    op.drop_table("books")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    # Drop enum types
    sa.Enum(name="copycondition").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="copystatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
