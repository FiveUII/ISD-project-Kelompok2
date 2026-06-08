"""
Health check endpoints.

GET /health       — liveness probe (no DB; used by load balancers)
GET /health/db    — readiness probe (real DB query; proves the stack is connected)
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.library_settings import LibrarySettings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def liveness() -> dict:
    """
    Liveness probe — returns 200 immediately without touching the database.
    Used by Docker healthchecks and load balancers.
    """
    return {"status": "ok"}


@router.get("/db")
async def readiness(session: AsyncSession = Depends(get_db)) -> dict:
    """
    Readiness probe — executes a real SELECT against library_settings.
    Returns the seeded loan_period_days value, proving the full DB round-trip works.
    """
    result = await session.execute(select(LibrarySettings).limit(1))
    settings_row = result.scalar_one_or_none()
    loan_period_days = settings_row.loan_period_days if settings_row else 14
    return {"status": "ok", "loan_period_days": loan_period_days}
