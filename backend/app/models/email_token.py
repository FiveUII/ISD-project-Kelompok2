"""
EmailToken model — stores single-use tokens for email verification and password reset.

token_type values:
  - "verify": email address verification (Plan 02)
  - "reset": password reset (Plan 03)

Security design:
  - token is a urlsafe random string (secrets.token_urlsafe), unique + indexed for fast lookup
  - expires_at enforces a finite TTL (24h for verify tokens)
  - used_at is set when the token is consumed; re-use returns 400
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class EmailToken(Base):
    __tablename__ = "email_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    token_type: Mapped[str] = mapped_column(
        String(20), nullable=False  # "verify" | "reset"
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<EmailToken id={self.id} user_id={self.user_id} "
            f"type={self.token_type!r} used={self.used_at is not None}>"
        )
