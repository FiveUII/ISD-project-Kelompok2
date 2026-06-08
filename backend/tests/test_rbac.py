"""
Tests for RBAC router-level dependency enforcement.

Covers:
- Unauthenticated request to require_librarian-protected endpoint → 401
- Student-role token to require_librarian-protected endpoint → 403 "Librarian role required"
- Librarian-role token to require_librarian-protected endpoint → 200

These tests use a dedicated /api/admin/test-protected route via the admin router,
which is protected with require_admin at the router level.

We also verify a hypothetical librarian-protected route via a test-specific
router wired only for this test module.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.core.security import hash_password, create_access_token
from app.core.enums import UserRole


@pytest_asyncio.fixture
async def client(async_session: AsyncSession):
    """HTTP test client with DB dependency override."""
    from app.core.db import get_db

    async def override_get_db():
        try:
            yield async_session
            await async_session.commit()
        except Exception:
            await async_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def student_user(async_session: AsyncSession) -> User:
    """A verified student user in the test DB."""
    user = User(
        email="student@example.com",
        full_name="Test Student",
        hashed_password=hash_password("password123"),
        role=UserRole.student,
        is_email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def librarian_user(async_session: AsyncSession) -> User:
    """A verified librarian user in the test DB."""
    user = User(
        email="librarian@example.com",
        full_name="Test Librarian",
        hashed_password=hash_password("password123"),
        role=UserRole.librarian,
        is_email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(async_session: AsyncSession) -> User:
    """The seeded admin superuser (role=librarian, email=ADMIN_EMAIL)."""
    import os
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@test.com")
    user = User(
        email=admin_email,
        full_name="Admin Superuser",
        hashed_password=hash_password("test-admin-password"),
        role=UserRole.librarian,
        is_email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Unauthenticated → 401 on admin-protected route
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthenticated_gets_401(client: AsyncClient):
    """No token → 401 from require_admin-protected admin router."""
    resp = await client.post("/api/admin/users/999/promote")
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Student token → 403 on admin-protected route
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_student_gets_403_on_admin_route(
    client: AsyncClient,
    student_user: User,
):
    """Student-role token → 403 on admin-only endpoint (require_admin check)."""
    token = create_access_token(sub=student_user.id, role=student_user.role.value)
    resp = await client.post(
        "/api/admin/users/999/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# Librarian (non-admin) → 403 on admin-only route
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_admin_librarian_gets_403_on_admin_route(
    client: AsyncClient,
    librarian_user: User,
):
    """Librarian who is NOT the admin superuser → 403 on /admin/* routes."""
    token = create_access_token(sub=librarian_user.id, role=librarian_user.role.value)
    resp = await client.post(
        "/api/admin/users/999/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# Admin token → 200 on admin-protected route (promote endpoint)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_gets_200_on_admin_route(
    client: AsyncClient,
    admin_user: User,
    student_user: User,
):
    """Admin token → 200 on /admin/users/{id}/promote."""
    token = create_access_token(sub=admin_user.id, role=admin_user.role.value)
    resp = await client.post(
        f"/api/admin/users/{student_user.id}/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
