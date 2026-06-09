"""Create loans table.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-09

Adds:
  - loans table tracking copy checkouts with due_date and returned_at
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "copy_id",
            sa.Integer,
            sa.ForeignKey("copies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "checked_out_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_loans_copy_id", "loans", ["copy_id"])
    op.create_index("ix_loans_user_id", "loans", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_loans_user_id", table_name="loans")
    op.drop_index("ix_loans_copy_id", table_name="loans")
    op.drop_table("loans")
