"""
Fine model — records fines for overdue loan returns.

A Fine row is created automatically by return_loan() when days_overdue > 0.
Amount = days_overdue * fine_rate_per_day (from library_settings).
Status lifecycle: unpaid -> paid | waived.
No direct client input into fine amount — computed server-side from DB timestamps.
(T-04-01 mitigated: amount derives from due_date/returned_at, not client input.)
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Fine(Base):
    __tablename__ = "fines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("loans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    days_overdue: Mapped[int] = mapped_column(Integer, nullable=False)
    # Status: "unpaid" (default), "paid", or "waived"
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="unpaid", server_default="unpaid"
    )
    waiver_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationship back to the loan
    loan: Mapped["Loan"] = relationship("Loan", back_populates="fines")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<Fine id={self.id} loan_id={self.loan_id} "
            f"amount={self.amount} status={self.status}>"
        )
