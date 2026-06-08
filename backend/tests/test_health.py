"""
Tests for health endpoints — TDD RED phase.
Tests GET /api/health and GET /api/health/db.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.db import Base
from app.models.library_settings import LibrarySettings


@pytest_asyncio.fixture
async def test_db_session():
    """Provide a test DB session with a seeded library_settings row."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        # Seed one settings row
        settings_row = LibrarySettings(
            loan_period_days=14,
            fine_rate_per_day="0.25",
            reminder_days_before=1,
        )
        session.add(settings_row)
        await session.commit()
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_app(test_db_session):
    """Create FastAPI test client with overridden DB dependency."""
    from app.main import app
    from app.core.db import get_db

    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_liveness(test_app):
    """GET /api/health returns 200 and {"status": "ok"} without touching DB."""
    response = await test_app.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_db(test_app):
    """GET /api/health/db returns 200 and loan_period_days read from library_settings."""
    response = await test_app.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "loan_period_days" in data
    assert data["loan_period_days"] == 14


@pytest.mark.asyncio
async def test_app_has_api_prefix(test_app):
    """The app mounts all health routes under /api prefix."""
    response = await test_app.get("/health")
    # Without /api prefix should return 404
    assert response.status_code == 404

    response = await test_app.get("/api/health")
    assert response.status_code == 200
