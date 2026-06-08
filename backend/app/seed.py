"""
Database seed functions.
These are idempotent: calling them multiple times is safe.
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import UserRole
from app.core.security import hash_password
from app.models.library_settings import LibrarySettings
from app.models.user import User

logger = logging.getLogger(__name__)


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


async def seed_admin_superuser(session: AsyncSession) -> None:
    """
    Seed the admin superuser from ADMIN_EMAIL / ADMIN_PASSWORD env vars.

    Creates a user with:
    - email = settings.ADMIN_EMAIL
    - hashed_password = Argon2(settings.ADMIN_PASSWORD)
    - role = librarian
    - is_email_verified = True (no email verification required for the seeded admin)

    Idempotent (D-03): if a user with ADMIN_EMAIL already exists, this is a no-op.
    PITFALLS C4: credentials come from env vars only — never hardcoded.
    """
    result = await session.execute(
        select(User).where(User.email == settings.ADMIN_EMAIL)
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        logger.info(
            "Admin superuser already exists (email=%s) — seed is a no-op.",
            settings.ADMIN_EMAIL,
        )
        return

    admin = User(
        email=settings.ADMIN_EMAIL,
        full_name="Library Admin",
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        role=UserRole.librarian,
        is_email_verified=True,
    )
    session.add(admin)
    logger.info(
        "Seeded admin superuser (email=%s).",
        settings.ADMIN_EMAIL,
    )
