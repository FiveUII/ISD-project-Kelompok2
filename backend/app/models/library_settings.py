"""
LibrarySettings model — system-wide configuration stored in the database.
No hardcoded loan period or fine rate constants (PITFALLS m3).
A librarian settings UI (Phase 3) will allow updating these without redeployment.
"""
from sqlalchemy import Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LibrarySettings(Base):
    __tablename__ = "library_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Default loan period: 14 days. Read from DB, never hardcoded in Python logic.
    loan_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    # Fine per day for overdue books: $0.25 default.
    fine_rate_per_day: Mapped[float] = mapped_column(
        Numeric(6, 2), nullable=False, default="0.25"
    )
    # How many days before due to send reminder email.
    reminder_days_before: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __repr__(self) -> str:
        return (
            f"<LibrarySettings id={self.id} "
            f"loan_period_days={self.loan_period_days} "
            f"fine_rate_per_day={self.fine_rate_per_day}>"
        )
