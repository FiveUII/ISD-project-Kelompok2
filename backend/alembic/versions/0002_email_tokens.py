"""Add email_tokens table for verification and password-reset tokens.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-08

Creates:
  - email_tokens table: id, user_id (FK users.id CASCADE), token (unique, indexed),
    token_type ('verify'|'reset'), expires_at (TIMESTAMPTZ), used_at (TIMESTAMPTZ nullable),
    created_at (TIMESTAMPTZ, default NOW())

T-02-05: single-use token enforced via used_at; urlsafe random token + 24h expiry.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(128), nullable=False),
        sa.Column("token_type", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_tokens_token", "email_tokens", ["token"], unique=True)
    op.create_index("ix_email_tokens_user_id", "email_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_email_tokens_user_id", table_name="email_tokens")
    op.drop_index("ix_email_tokens_token", table_name="email_tokens")
    op.drop_table("email_tokens")
