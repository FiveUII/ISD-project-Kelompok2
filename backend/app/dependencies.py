"""
Shared FastAPI dependencies for authentication and RBAC.

Role-Based Access Control is enforced via DI at the APIRouter level — NOT via
inline `if` statements in handlers and NOT via middleware.
(PITFALLS C4 — anti-pattern: per-route inline role checks)

Usage:
    # Router-level protection (preferred — PITFALLS C4):
    router = APIRouter(
        prefix="/admin",
        dependencies=[Depends(require_admin)],
    )

    # Per-route protection when needed:
    @router.get("/something")
    async def something(user: User = Depends(require_librarian)):
        ...
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import decode_access_token
from app.core.enums import UserRole
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that:
    1. Extracts the Bearer token from the Authorization header.
    2. Decodes and verifies the JWT signature + expiry.
    3. Loads the User row from the database by the `sub` claim.
    4. Returns the User (with the DB-authoritative role).

    Role is always read from the DB record, NOT from the JWT payload.
    (PITFALLS Anti-Pattern 3 — never trust role claims in the token.)

    Raises:
        HTTPException 401: missing/invalid/expired token, or user not found in DB.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def require_librarian(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    RBAC dependency: require librarian (or admin) role.

    Use at APIRouter level (not per-route inline checks — PITFALLS C4):
        router = APIRouter(dependencies=[Depends(require_librarian)])

    Raises:
        HTTPException 401: no/invalid/expired token (from get_current_user)
        HTTPException 403: user exists but role is not librarian
    """
    if current_user.role != UserRole.librarian:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Librarian role required",
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    RBAC dependency: require the seeded admin superuser.

    In v1, the admin is identified by role==librarian AND email==settings.ADMIN_EMAIL.
    Only the seeded superuser can call /admin/* endpoints — no other librarians can
    promote users (D-03, D-05).

    Use at APIRouter level (not per-route inline checks — PITFALLS C4):
        router = APIRouter(dependencies=[Depends(require_admin)])

    Raises:
        HTTPException 401: no/invalid/expired token (from get_current_user)
        HTTPException 403: user is not the seeded admin superuser
    """
    admin_email = settings.ADMIN_EMAIL.strip().lower()
    user_email = current_user.email.strip().lower()
    if current_user.role != UserRole.librarian or user_email != admin_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
