"""
Tests for /auth/register and /auth/verify-email endpoints.
Covers:
- POST /api/auth/register: 201, duplicate email 409, EmailToken created, password hashed
- GET /api/auth/verify-email: valid token → verified=True, invalid/expired → 400
- Password round-trip: verify_password(plain, hash) True/False
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# App imports
from app.main import app
from app.models.user import User
from app.models.email_token import EmailToken
from app.core.security import hash_password, verify_password


@pytest_asyncio.fixture
async def client(async_session: AsyncSession):
    """HTTP test client that overrides the DB dependency with the test session."""
    from app.core.db import get_db

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Password round-trip
# ---------------------------------------------------------------------------

def test_hash_password_not_plaintext():
    """hash_password must NOT return the original string."""
    plain = "mysecretpassword"
    hashed = hash_password(plain)
    assert hashed != plain


def test_verify_password_correct():
    """verify_password returns True for the matching plaintext."""
    plain = "correct-horse-battery"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_wrong():
    """verify_password returns False for wrong plaintext."""
    hashed = hash_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, async_session: AsyncSession):
    """Successful registration returns 201 and creates an unverified student."""
    payload = {
        "email": "student@example.com",
        "password": "securepass123",
        "full_name": "Test Student",
    }
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, resp.text

    body = resp.json()
    assert body["email"] == payload["email"]
    assert body["full_name"] == payload["full_name"]
    assert body["role"] == "student"
    assert body["is_email_verified"] is False


@pytest.mark.asyncio
async def test_register_password_hashed(client: AsyncClient, async_session: AsyncSession):
    """Registered user's hashed_password must not equal the plaintext."""
    payload = {
        "email": "hashcheck@example.com",
        "password": "plaintextpassword",
        "full_name": "Hash Check",
    }
    await client.post("/api/auth/register", json=payload)

    # Load the user directly from DB
    result = await async_session.execute(
        select(User).where(User.email == payload["email"])
    )
    user = result.scalar_one()
    assert user.hashed_password != payload["password"]
    # Verify Argon2 round-trip
    assert verify_password(payload["password"], user.hashed_password) is True


@pytest.mark.asyncio
async def test_register_creates_email_token(client: AsyncClient, async_session: AsyncSession):
    """Registration must create an EmailToken row of type 'verify' for the new user."""
    payload = {
        "email": "tokencheck@example.com",
        "password": "securepass123",
        "full_name": "Token Check",
    }
    await client.post("/api/auth/register", json=payload)

    # Find the user
    result = await async_session.execute(
        select(User).where(User.email == payload["email"])
    )
    user = result.scalar_one()

    # Find their token
    token_result = await async_session.execute(
        select(EmailToken).where(EmailToken.user_id == user.id)
    )
    token = token_result.scalar_one()
    assert token.token_type == "verify"
    assert token.used_at is None
    assert token.expires_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, async_session: AsyncSession):
    """Registering with an already-used email returns 409."""
    payload = {
        "email": "duplicate@example.com",
        "password": "securepass123",
        "full_name": "First User",
    }
    resp1 = await client.post("/api/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/auth/register", json=payload)
    assert resp2.status_code == 409


# ---------------------------------------------------------------------------
# GET /api/auth/verify-email
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_email_valid_token(client: AsyncClient, async_session: AsyncSession):
    """Valid verify token sets is_email_verified=True and returns 200."""
    payload = {
        "email": "verify@example.com",
        "password": "securepass123",
        "full_name": "Verify User",
    }
    await client.post("/api/auth/register", json=payload)

    # Retrieve the token from DB
    user_result = await async_session.execute(
        select(User).where(User.email == payload["email"])
    )
    user = user_result.scalar_one()
    token_result = await async_session.execute(
        select(EmailToken).where(EmailToken.user_id == user.id)
    )
    email_token = token_result.scalar_one()

    resp = await client.get(f"/api/auth/verify-email?token={email_token.token}")
    assert resp.status_code == 200

    # Refresh user from DB
    await async_session.refresh(user)
    assert user.is_email_verified is True


@pytest.mark.asyncio
async def test_verify_email_invalid_token(client: AsyncClient):
    """An invalid/nonexistent token returns 400."""
    resp = await client.get("/api/auth/verify-email?token=totally-invalid-token-xyz")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_already_used(client: AsyncClient, async_session: AsyncSession):
    """A verification token can only be used once; a second use returns 400."""
    payload = {
        "email": "reuse@example.com",
        "password": "securepass123",
        "full_name": "Reuse Test",
    }
    await client.post("/api/auth/register", json=payload)

    user_result = await async_session.execute(
        select(User).where(User.email == payload["email"])
    )
    user = user_result.scalar_one()
    token_result = await async_session.execute(
        select(EmailToken).where(EmailToken.user_id == user.id)
    )
    email_token = token_result.scalar_one()

    # Use once
    await client.get(f"/api/auth/verify-email?token={email_token.token}")
    # Use again
    resp = await client.get(f"/api/auth/verify-email?token={email_token.token}")
    assert resp.status_code == 400
