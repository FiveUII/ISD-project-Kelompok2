"""
Admin router — protected endpoints for admin superuser operations.

All endpoints under /admin are protected at the ROUTER level with require_admin.
This is the correct RBAC pattern (PITFALLS C4) — NOT inline role checks in handlers.

Wired into main.py as: app.include_router(admin.router, prefix="/api")
Full paths:
  POST /api/admin/users/{user_id}/promote

D-03: Only the seeded admin superuser (ADMIN_EMAIL) can call these endpoints.
D-05: No admin UI — API endpoint only (Swagger / curl).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies import require_admin
from app.schemas.auth import UserResponse
from app.services.auth_service import promote_user_to_librarian

# Protection declared at the ROUTER level — every endpoint in this router
# requires admin access (role=librarian AND email=ADMIN_EMAIL).
# This satisfies PITFALLS C4: no per-route inline role checks.
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.post("/users/{user_id}/promote", response_model=UserResponse)
async def promote_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Promote a registered account to librarian role.

    Only callable by the seeded admin superuser (D-03, D-05).
    Returns the updated user profile with role=librarian.

    Raises:
        403: caller is not the admin superuser (enforced at router level)
        404: user with the given ID does not exist
    """
    user = await promote_user_to_librarian(session, user_id)
    return user
