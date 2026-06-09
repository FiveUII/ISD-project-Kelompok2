"""
Loan model — one row per physical copy checkout event.

Tracks: which copy is checked out, to which user, when, and when returned.
The is_overdue property is computed at query time (due_date < now()) — there is
no stored status field for overdue (CONTEXT D-01: overdue computed at query time,
no background job needed in Phase 3).
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    copy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("copies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    checked_out_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    copy: Mapped["Copy"] = relationship("Copy", back_populates="loans")  # type: ignore[name-defined]
    borrower: Mapped["User"] = relationship("User", back_populates="loans")  # type: ignore[name-defined]
    fines: Mapped[list["Fine"]] = relationship("Fine", back_populates="loan")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<Loan id={self.id} copy_id={self.copy_id} "
            f"user_id={self.user_id} returned_at={self.returned_at}>"
        )
