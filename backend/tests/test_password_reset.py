"""
Tests for the password-reset flow (AUTH-03).

Covers:
- POST /api/auth/forgot-password with a known email → 200 + creates reset EmailToken
- POST /api/auth/forgot-password with an unknown email → 200 (no user enumeration, T-03-04)
- POST /api/auth/reset-password with a valid token + new password → 200, hash updated,
  old password no longer verifies, new one does, token marked used
- POST /api/auth/reset-password with an already-used token → 400
- POST /api/auth/reset-password with an expired token → 400
- After reset, user can log in with the new password (integration via authenticate_user)
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.models.email_token import EmailToken
from app.core.security import hash_password, verify_password, create_access_token
from app.core.enums import UserRole
from app.services.auth_service import authenticate_user


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
async def verified_user(async_session: AsyncSession) -> User:
    """A verified student user in the test DB."""
    user = User(
        email="resetuser@example.com",
        full_name="Reset Test User",
        hashed_password=hash_password("oldpassword123"),
        role=UserRole.student,
        is_email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# POST /api/auth/forgot-password
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forgot_password_known_email_returns_200(
    client: AsyncClient,
    verified_user: User,
    async_session: AsyncSession,
):
    """Known email → 200 and a reset token is created in the DB."""
    resp = await client.post(
        "/api/auth/forgot-password",
        json={"email": "resetuser@example.com"},
    )
    assert resp.status_code == 200, resp.text

    # A reset EmailToken must have been created
    result = await async_session.execute(
        select(EmailToken).where(
            EmailToken.user_id == verified_user.id,
            EmailToken.token_type == "reset",
        )
    )
    token_row = result.scalar_one_or_none()
    assert token_row is not None
    assert token_row.used_at is None  # not yet used


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_returns_200(client: AsyncClient):
    """Unknown email → 200 (no user enumeration — T-03-04)."""
    resp = await client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# POST /api/auth/reset-password (valid token)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_password_valid_token_updates_hash(
    client: AsyncClient,
    verified_user: User,
    async_session: AsyncSession,
):
    """Valid reset token + new password → 200, hash updated, token marked used."""
    # First: create a reset token via forgot-password
    await client.post(
        "/api/auth/forgot-password",
        json={"email": "resetuser@example.com"},
    )

    # Fetch the token from DB
    result = await async_session.execute(
        select(EmailToken).where(
            EmailToken.user_id == verified_user.id,
            EmailToken.token_type == "reset",
        )
    )
    token_row = result.scalar_one()
    raw_token = token_row.token

    # Now reset the password
    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "newpassword456"},
    )
    assert resp.status_code == 200, resp.text

    # Refresh and verify: old password no longer works
    await async_session.refresh(verified_user)
    assert not verify_password("oldpassword123", verified_user.hashed_password)
    assert verify_password("newpassword456", verified_user.hashed_password)

    # Token marked as used
    await async_session.refresh(token_row)
    assert token_row.used_at is not None


@pytest.mark.asyncio
async def test_reset_password_reused_token_returns_400(
    client: AsyncClient,
    verified_user: User,
    async_session: AsyncSession,
):
    """Reusing an already-used reset token → 400."""
    await client.post(
        "/api/auth/forgot-password",
        json={"email": "resetuser@example.com"},
    )

    result = await async_session.execute(
        select(EmailToken).where(
            EmailToken.user_id == verified_user.id,
            EmailToken.token_type == "reset",
        )
    )
    token_row = result.scalar_one()
    raw_token = token_row.token

    # Use the token once
    await client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "newpassword456"},
    )

    # Try again — should 400
    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "anotherpassword789"},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_reset_password_expired_token_returns_400(
    client: AsyncClient,
    verified_user: User,
    async_session: AsyncSession,
):
    """Expired reset token → 400."""
    # Manually insert an expired token
    expired_token = EmailToken(
        user_id=verified_user.id,
        token="expiredtoken12345",
        token_type="reset",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=2),  # 2h in the past
    )
    async_session.add(expired_token)
    await async_session.commit()

    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": "expiredtoken12345", "new_password": "newpassword456"},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_reset_password_invalid_token_returns_400(client: AsyncClient):
    """Non-existent reset token → 400."""
    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": "doesnotexist", "new_password": "newpassword456"},
    )
    assert resp.status_code == 400, resp.text


# ---------------------------------------------------------------------------
# Integration: login with new password after reset
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_with_new_password_after_reset(
    client: AsyncClient,
    verified_user: User,
    async_session: AsyncSession,
):
    """After password reset, user can log in with the new password."""
    # Request reset
    await client.post(
        "/api/auth/forgot-password",
        json={"email": "resetuser@example.com"},
    )

    result = await async_session.execute(
        select(EmailToken).where(
            EmailToken.user_id == verified_user.id,
            EmailToken.token_type == "reset",
        )
    )
    token_row = result.scalar_one()

    # Reset password
    await client.post(
        "/api/auth/reset-password",
        json={"token": token_row.token, "new_password": "brandnewpassword99"},
    )

    # Refresh user and try to authenticate with new password
    await async_session.refresh(verified_user)
    user = await authenticate_user(async_session, "resetuser@example.com", "brandnewpassword99")
    assert user is not None
    assert user.id == verified_user.id
