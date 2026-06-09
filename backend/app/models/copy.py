"""
Copy model — one physical library item. One row per physical copy on the shelf.

Loans reference Copy (not Book), enabling individual-copy tracking.
Availability = COUNT(copies WHERE status='available' AND book_id=X).
"""
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.enums import CopyCondition, CopyStatus


class Copy(Base):
    __tablename__ = "copies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("books.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    condition: Mapped[CopyCondition] = mapped_column(
        Enum(CopyCondition, name="copycondition"), nullable=False, default=CopyCondition.good
    )
    status: Mapped[CopyStatus] = mapped_column(
        Enum(CopyStatus, name="copystatus"), nullable=False, default=CopyStatus.available
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Soft-delete (PITFALLS m2): preserve loan history when a copy is lost/decommissioned.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship to parent Book
    book: Mapped["Book"] = relationship("Book", back_populates="copies")  # type: ignore[name-defined]

    # Relationship to loans (one copy can have multiple loans over time)
    loans: Mapped[list["Loan"]] = relationship("Loan", back_populates="copy")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Copy id={self.id} book_id={self.book_id} status={self.status}>"
