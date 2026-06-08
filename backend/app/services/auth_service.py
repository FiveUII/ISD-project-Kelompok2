"""
Authentication service layer.

Business logic for:
- register_user: create unverified account + email verification token
- verify_email_token: flip is_email_verified on a valid, unused, unexpired token
- authenticate_user: verify credentials, enforce email-verified gate (D-01)
- promote_user_to_librarian: elevate a registered account to librarian role (D-03)
- request_password_reset: issue a reset token and log the link (AUTH-03)
- reset_password: validate token, update password, mark token used (AUTH-03)

PITFALLS Anti-Pattern 3: get_current_user (see app/dependencies.py) MUST load
the User row from DB — do NOT trust the role claim in the JWT payload for
authorization decisions.
"""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token
from app.core.enums import UserRole
from app.models.email_token import EmailToken
from app.models.user import User
from app.schemas.auth import RegisterRequest


async def register_user(session: AsyncSession, data: RegisterRequest) -> User:
    """
    Create an unverified student account and issue a verification token.

    Raises:
        HTTPException 409: email already registered
        HTTPException 422: password too short (< 8 chars)
    """
    if len(data.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    # Check for duplicate email
    existing = await session.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create unverified user
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        is_email_verified=False,
    )
    session.add(user)
    await session.flush()  # assign user.id without committing

    # Create email verification token (24h TTL)
    raw_token = secrets.token_urlsafe(32)
    email_token = EmailToken(
        user_id=user.id,
        token=raw_token,
        token_type="verify",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(email_token)
    await session.flush()

    # Send (log) the verification email — Phase 4 will swap this for real SMTP
    from app.services.email_service import send_verification_email
    await send_verification_email(user.email, raw_token)

    return user


async def verify_email_token(session: AsyncSession, token: str) -> User:
    """
    Mark a user's email as verified using a valid, unused, unexpired verify token.

    Raises:
        HTTPException 400: token not found, already used, expired, or wrong type
    """
    result = await session.execute(
        select(EmailToken).where(EmailToken.token == token)
    )
    email_token = result.scalar_one_or_none()

    if email_token is None:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    if email_token.token_type != "verify":
        raise HTTPException(status_code=400, detail="Invalid verification token")
    if email_token.used_at is not None:
        raise HTTPException(status_code=400, detail="Verification token already used")
    # Handle both timezone-aware (PostgreSQL) and naive (SQLite/aiosqlite tests)
    now_utc = datetime.now(timezone.utc)
    expires_at = email_token.expires_at
    if expires_at.tzinfo is None:
        # SQLite returns naive datetimes — compare as naive
        now_utc = now_utc.replace(tzinfo=None)
    if expires_at < now_utc:
        raise HTTPException(status_code=400, detail="Verification token has expired")

    # Mark token as used
    email_token.used_at = datetime.now(timezone.utc)

    # Mark user as verified
    user_result = await session.execute(
        select(User).where(User.id == email_token.user_id)
    )
    user = user_result.scalar_one()
    user.is_email_verified = True

    return user


async def promote_user_to_librarian(session: AsyncSession, user_id: int) -> User:
    """
    Promote a registered account to librarian role.

    Called only by the seeded admin superuser via POST /api/admin/users/{id}/promote.
    Only the /admin router enforces the require_admin gate (D-03, D-05).

    Raises:
        HTTPException 404: user with the given ID does not exist
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = UserRole.librarian
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    """
    Authenticate a user by email + password.

    Raises:
        HTTPException 401: user not found or wrong password
        HTTPException 403: email not yet verified (D-01 strict block)
    """
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # D-01: block login until email is verified (strict block, not just warning)
    if not user.is_email_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your inbox and click the verification link.",
        )

    return user


async def request_password_reset(session: AsyncSession, email: str) -> None:
    """
    Issue a password-reset token for the given email address.

    If the email exists in the DB, creates a reset EmailToken (type="reset", 1h TTL)
    and calls send_password_reset_email (logs in dev, SMTP in Phase 4).

    ALWAYS returns successfully — never reveals whether the email exists.
    (T-03-04: no user enumeration on forgot-password)
    """
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        # No user — return silently to prevent user enumeration
        return

    # Create a single-use reset token with a 1-hour expiry (T-03-03)
    raw_token = secrets.token_urlsafe(32)
    reset_token = EmailToken(
        user_id=user.id,
        token=raw_token,
        token_type="reset",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    session.add(reset_token)
    await session.flush()

    # Log (dev) / send (Phase 4) the reset email
    from app.services.email_service import send_password_reset_email
    await send_password_reset_email(user.email, raw_token)


async def reset_password(session: AsyncSession, token: str, new_password: str) -> None:
    """
    Set a new password using a valid, unused, unexpired reset token.

    Marks the token as used so it cannot be replayed (T-03-03).

    Raises:
        HTTPException 400: token not found, already used, expired, or wrong type
    """
    result = await session.execute(
        select(EmailToken).where(EmailToken.token == token)
    )
    reset_token = result.scalar_one_or_none()

    if reset_token is None:
        raise HTTPException(status_code=400, detail="Invalid password reset token")
    if reset_token.token_type != "reset":
        raise HTTPException(status_code=400, detail="Invalid password reset token")
    if reset_token.used_at is not None:
        raise HTTPException(status_code=400, detail="Password reset token already used")

    # Handle both timezone-aware (PostgreSQL) and naive (SQLite/aiosqlite tests)
    now_utc = datetime.now(timezone.utc)
    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=None)
    if expires_at < now_utc:
        raise HTTPException(status_code=400, detail="Password reset token has expired")

    # Load the user and update the password hash
    user_result = await session.execute(
        select(User).where(User.id == reset_token.user_id)
    )
    user = user_result.scalar_one()
    user.hashed_password = hash_password(new_password)

    # Mark token as used (single-use enforcement — T-03-03)
    reset_token.used_at = datetime.now(timezone.utc)
