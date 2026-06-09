"""Add pg_trgm GIN indexes on books.title and books.author for ILIKE catalog search.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-09

Adds:
  - pg_trgm extension (required for trigram-based GIN indexes)
  - ix_books_title_trgm GIN index on books.title  (accelerates ILIKE '%q%' substring search)
  - ix_books_author_trgm GIN index on books.author (accelerates ILIKE '%q%' substring search)

Note: B-tree indexes cannot accelerate ILIKE '%q%' patterns; only pg_trgm GIN indexes
can, because they index character trigrams rather than sorted column values.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX ix_books_title_trgm ON books USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_books_author_trgm ON books USING gin (author gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_books_author_trgm")
    op.execute("DROP INDEX IF EXISTS ix_books_title_trgm")
