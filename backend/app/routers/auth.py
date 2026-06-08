"""
Auth router — public endpoints for register, verify-email, login, /me, and password reset.

All endpoints under /auth are PUBLIC except /auth/me which requires a valid JWT.

Wired into main.py as: app.include_router(auth.router, prefix="/api")
This means the full paths are:
  POST /api/auth/register
  GET  /api/auth/verify-email?token=...
  POST /api/auth/login
  GET  /api/auth/me
  POST /api/auth/forgot-password
  POST /api/auth/reset-password
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import create_access_token
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    register_user,
    request_password_reset,
    reset_password,
    verify_email_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Register a new student account.
    Returns the created user (unverified, role=student).
    The verification email is logged (dev) or sent (production Phase 4).
    """
    return await register_user(session, data)


@router.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Verify the user's email address using the token from the verification link.
    On success sets is_email_verified=True and returns a confirmation message.
    """
    await verify_email_token(session, token)
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate with email + password.
    Returns a 24h JWT access token.
    Returns 403 if email is not yet verified (D-01 strict block).
    """
    user = await authenticate_user(session, data.email, data.password)
    token = create_access_token(sub=user.id, role=user.role.value)
    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """
    Return the authenticated user's profile.
    Role is read from the DB record, not the JWT (PITFALLS Anti-Pattern 3).
    """
    return current_user


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    data: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Request a password-reset link for the given email address.

    Always returns 200 regardless of whether the email exists in the DB —
    this prevents user enumeration (T-03-04).

    The reset link is logged in dev; Phase 4 will send it via SMTP.
    """
    await request_password_reset(session, data.email)
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password_endpoint(
    data: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Set a new password using the token from the reset email.

    The token is single-use and has a 1-hour expiry (T-03-03).
    Returns 400 for invalid, already-used, or expired tokens.
    """
    await reset_password(session, data.token, data.new_password)
    return {"message": "Password updated successfully. You can now log in with your new password."}
