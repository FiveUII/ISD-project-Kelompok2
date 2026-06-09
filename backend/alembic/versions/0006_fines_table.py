"""Create fines table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-09

Adds:
  - fines table for recording overdue loan fines
    (loan_id FK, amount, days_overdue, status, waiver_reason, created_at)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "loan_id",
            sa.Integer,
            sa.ForeignKey("loans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(8, 2), nullable=False),
        sa.Column("days_overdue", sa.Integer, nullable=False),
        sa.Column(
            "status", sa.String(10), nullable=False, server_default="unpaid"
        ),
        sa.Column("waiver_reason", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_fines_loan_id", "fines", ["loan_id"])


def downgrade() -> None:
    op.drop_index("ix_fines_loan_id", table_name="fines")
    op.drop_table("fines")
