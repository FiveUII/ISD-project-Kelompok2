"""
Admin router — protected endpoints for admin superuser operations.

All endpoints under /admin are protected at the ROUTER level with require_admin.
This is the correct RBAC pattern (PITFALLS C4) — NOT inline role checks in handlers.

Wired into main.py as: app.include_router(admin.router, prefix="/api")
Full paths:
  POST /api/admin/users/{user_id}/promote
  GET  /api/admin/users?role=student&search=query  (for checkout student search in Phase 3)

D-03: Only the seeded admin superuser (ADMIN_EMAIL) can call these endpoints.
D-05: No admin UI — API endpoint only (Swagger / curl).

Phase 3 note: GET /api/admin/users is used by the checkout modal's student search —
protected by require_admin, which means only the librarian admin can call it.
This is acceptable in v1 since only the admin librarian account processes checkouts.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.enums import UserRole
from app.dependencies import require_admin
from app.models.user import User
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


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """
    List users, optionally filtered by role and search query.

    GET /api/admin/users?role=student&search=alice

    Used by the checkout modal's student search (Phase 3 Plan 02).
    Returns users matching the role filter and search term (email/name ILIKE).

    Only callable by the seeded admin superuser (D-03).
    """
    filters = [User.deleted_at.is_(None)]

    if role:
        try:
            role_enum = UserRole(role)
            filters.append(User.role == role_enum)
        except ValueError:
            pass  # Unknown role value — ignore filter, return all

    if search:
        filters.append(
            or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
            )
        )

    result = await session.execute(
        select(User).where(and_(*filters)).order_by(User.email).limit(20)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


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
