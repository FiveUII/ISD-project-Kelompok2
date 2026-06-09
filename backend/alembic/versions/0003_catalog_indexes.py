"""Add search indexes on books.title and books.author for ILIKE catalog search performance.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-09

Adds:
  - ix_books_title index on books.title (improves ILIKE title search)
  - ix_books_author index on books.author (improves ILIKE author search)
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_books_title", "books", ["title"])
    op.create_index("ix_books_author", "books", ["author"])


def downgrade() -> None:
    op.drop_index("ix_books_author", table_name="books")
    op.drop_index("ix_books_title", table_name="books")
