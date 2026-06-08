"""
Tests for admin superuser seeding and role promotion endpoint.

Covers:
- seed_admin_superuser creates a user with role=librarian, is_email_verified=True
  from ADMIN_EMAIL/ADMIN_PASSWORD env vars
- Calling seed_admin_superuser a second time is a no-op (idempotent, D-03)
- POST /api/admin/users/{id}/promote as admin → 200 + role=librarian
- POST /api/admin/users/{id}/promote as student → 403
- POST /api/admin/users/{id}/promote without auth → 401
- POST /api/admin/users/{id}/promote for non-existent user → 404
"""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token
from app.core.enums import UserRole
from app.seed import seed_admin_superuser


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
        email="student_promote@example.com",
        full_name="Student to Promote",
        hashed_password=hash_password("password123"),
        role=UserRole.student,
        is_email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(async_session: AsyncSession) -> User:
    """The seeded admin superuser (role=librarian, email=ADMIN_EMAIL)."""
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@test.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "test-admin-password")
    user = User(
        email=admin_email,
        full_name="Admin Superuser",
        hashed_password=hash_password(admin_password),
        role=UserRole.librarian,
        is_email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# seed_admin_superuser: idempotent seed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_admin_creates_user(async_session: AsyncSession):
    """seed_admin_superuser inserts admin with role=librarian and is_email_verified=True."""
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@test.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "test-admin-password")

    await seed_admin_superuser(async_session)
    await async_session.commit()

    result = await async_session.execute(select(User).where(User.email == admin_email))
    user = result.scalar_one_or_none()

    assert user is not None
    assert user.role == UserRole.librarian
    assert user.is_email_verified is True
    assert verify_password(admin_password, user.hashed_password)


@pytest.mark.asyncio
async def test_seed_admin_is_idempotent(async_session: AsyncSession):
    """Calling seed_admin_superuser twice creates exactly one user (no duplicate, no error)."""
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@test.com")

    await seed_admin_superuser(async_session)
    await async_session.commit()
    await seed_admin_superuser(async_session)
    await async_session.commit()

    result = await async_session.execute(select(User).where(User.email == admin_email))
    users = result.scalars().all()
    assert len(users) == 1


# ---------------------------------------------------------------------------
# POST /api/admin/users/{id}/promote
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_promote_as_admin_succeeds(
    client: AsyncClient,
    admin_user: User,
    student_user: User,
    async_session: AsyncSession,
):
    """Admin promotes a student to librarian → 200 with role=librarian in response."""
    token = create_access_token(sub=admin_user.id, role=admin_user.role.value)
    resp = await client.post(
        f"/api/admin/users/{student_user.id}/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == "librarian"
    assert body["id"] == student_user.id


@pytest.mark.asyncio
async def test_promote_as_student_forbidden(
    client: AsyncClient,
    student_user: User,
):
    """Student token → 403 on promote endpoint."""
    token = create_access_token(sub=student_user.id, role=student_user.role.value)
    resp = await client.post(
        f"/api/admin/users/{student_user.id}/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_promote_unauthenticated(client: AsyncClient, student_user: User):
    """No auth → 401 on promote endpoint."""
    resp = await client.post(f"/api/admin/users/{student_user.id}/promote")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_promote_nonexistent_user(
    client: AsyncClient,
    admin_user: User,
):
    """Admin trying to promote a non-existent user → 404."""
    token = create_access_token(sub=admin_user.id, role=admin_user.role.value)
    resp = await client.post(
        "/api/admin/users/99999/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, resp.text
