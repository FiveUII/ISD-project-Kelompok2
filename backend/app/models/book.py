"""
Book model — bibliographic record. One row per unique edition/title.

CRITICAL: Book has NO availability/quantity columns (PITFALLS C1).
Availability is computed from Copy rows WHERE status='available'.
Physical items are tracked in the Copy model (separate table).
"""
from datetime import datetime
from sqlalchemy import DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isbn: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publish_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Soft-delete (PITFALLS m2): preserve copy + loan history when a title is retired.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship to physical copies (back_populates defined on Copy side)
    copies: Mapped[list["Copy"]] = relationship("Copy", back_populates="book")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Book id={self.id} isbn={self.isbn!r} title={self.title!r}>"
