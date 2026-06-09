"""Add notification sent flags to loans table.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-09

Adds:
  - loans.reminder_sent_at (nullable DateTime) — set after due-date reminder email sent
  - loans.overdue_sent_at (nullable DateTime) — set after overdue alert email sent

These columns prevent duplicate sends across APScheduler runs (T-04-08).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "loans",
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "loans",
        sa.Column("overdue_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("loans", "overdue_sent_at")
    op.drop_column("loans", "reminder_sent_at")
