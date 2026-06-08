"""
Database seed functions.
These are idempotent: calling them multiple times is safe.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library_settings import LibrarySettings


async def seed_library_settings(session: AsyncSession) -> None:
    """
    Insert the default LibrarySettings row if none exists.
    Idempotent: a no-op if a settings row already exists.
    """
    result = await session.execute(select(LibrarySettings).limit(1))
    existing = result.scalar_one_or_none()
    if existing is None:
        settings_row = LibrarySettings(
            loan_period_days=14,
            fine_rate_per_day="0.25",
            reminder_days_before=1,
        )
        session.add(settings_row)
        await session.commit()
