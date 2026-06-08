"""
Tests for /auth/login and /auth/me endpoints.
Covers:
- POST /api/auth/login with correct credentials for verified user → 200 + valid JWT
- POST /api/auth/login for unverified user → 403 (D-01 strict block)
- POST /api/auth/login with wrong password → 401
- GET /api/auth/me with valid token → 200 with user profile
- GET /api/auth/me without token → 401
"""
import pytest
import pytest_asyncio
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# App imports
from app.main import app
from app.models.user import User
from app.models.email_token import EmailToken
from app.core.security import hash_password, create_access_token


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
        email="verified@example.com",
        full_name="Verified Student",
        hashed_password=hash_password("correctpassword"),
        is_email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user(async_session: AsyncSession) -> User:
    """An unverified student user in the test DB."""
    user = User(
        email="unverified@example.com",
        full_name="Unverified Student",
        hashed_password=hash_password("correctpassword"),
        is_email_verified=False,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_verified_user_success(
    client: AsyncClient,
    verified_user: User,
):
    """Verified user with correct credentials receives a 200 and a valid access_token."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": "verified@example.com", "password": "correctpassword"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"

    # Token must be decodable and contain the user id as 'sub'
    import os
    secret = os.environ.get("JWT_SECRET", "test-secret-do-not-use-in-production")
    payload = pyjwt.decode(body["access_token"], secret, algorithms=["HS256"])
    assert payload["sub"] == str(verified_user.id)


@pytest.mark.asyncio
async def test_login_unverified_user_blocked(
    client: AsyncClient,
    unverified_user: User,
):
    """Unverified user gets 403 — email verification required (D-01 strict block)."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": "unverified@example.com", "password": "correctpassword"},
    )
    assert resp.status_code == 403, resp.text
    # Error message must indicate email verification, not just "unauthorized"
    detail = resp.json()["detail"].lower()
    assert "verif" in detail or "verified" in detail


@pytest.mark.asyncio
async def test_login_wrong_password(
    client: AsyncClient,
    verified_user: User,
):
    """Wrong password returns 401."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": "verified@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    """Non-existent email returns 401 (same as wrong password — no user enumeration)."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "somepassword"},
    )
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_me_with_valid_token(
    client: AsyncClient,
    verified_user: User,
):
    """GET /auth/me with a valid bearer token returns the user profile."""
    # Issue a token for the verified user
    token = create_access_token(sub=verified_user.id, role=verified_user.role.value)
    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["id"] == verified_user.id
    assert body["email"] == "verified@example.com"
    assert body["role"] == "student"
    assert body["is_email_verified"] is True


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    """GET /auth/me without Authorization header returns 401."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_me_with_invalid_token(client: AsyncClient):
    """GET /auth/me with a malformed token returns 401."""
    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer totally.invalid.token"},
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_me_with_expired_token(
    client: AsyncClient,
    verified_user: User,
):
    """GET /auth/me with an expired token returns 401."""
    import os
    secret = os.environ.get("JWT_SECRET", "test-secret-do-not-use-in-production")
    expired_payload = {
        "sub": str(verified_user.id),
        "role": "student",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # already expired
    }
    expired_token = pyjwt.encode(expired_payload, secret, algorithm="HS256")

    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401, resp.text
