"""Add 'new' value to copycondition enum.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-09

Adds:
  - 'new' variant to the copycondition PostgreSQL enum type
    (mirrors the CopyCondition.new addition in app/core/enums.py)
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block on older
    # PostgreSQL. Alembic's execute() uses the connection directly.
    op.execute("ALTER TYPE copycondition ADD VALUE IF NOT EXISTS 'new'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    # Downgrade is a no-op; remove the 'new' variant manually if needed.
    pass
