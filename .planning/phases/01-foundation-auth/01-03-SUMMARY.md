---
phase: 01-foundation-auth
plan: 03
subsystem: auth
tags: [fastapi, rbac, jwt, postgresql, sqlalchemy, argon2, react, password-reset]

# Dependency graph
requires:
  - phase: 01-foundation-auth/01-02
    provides: get_current_user DI, EmailToken model, email verification flow, JWT helpers

provides:
  - require_librarian and require_admin FastAPI DI dependencies (router-level RBAC)
  - POST /api/admin/users/{id}/promote (admin-only librarian promotion)
  - Idempotent admin superuser seed from ADMIN_EMAIL/ADMIN_PASSWORD env vars
  - POST /api/auth/forgot-password and POST /api/auth/reset-password endpoints
  - ForgotPassword.tsx and ResetPassword.tsx React pages

affects: [02-catalog, 03-borrowing, 04-notifications, all phases using require_librarian/require_admin]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Router-level RBAC via APIRouter dependencies=[Depends(require_admin)] — not per-route inline checks (PITFALLS C4)"
    - "Admin gated by role==librarian AND email==settings.ADMIN_EMAIL (single seeded superuser pattern)"
    - "Password reset with urlsafe random token, single-use (used_at), 1h expiry — no user enumeration"
    - "Idempotent seed: check existence before insert, no-op on re-run"

key-files:
  created:
    - backend/app/routers/admin.py
    - backend/tests/test_rbac.py
    - backend/tests/test_admin_promote.py
    - backend/tests/test_password_reset.py
    - frontend/src/pages/ForgotPassword.tsx
    - frontend/src/pages/ResetPassword.tsx
  modified:
    - backend/app/dependencies.py
    - backend/app/routers/auth.py
    - backend/app/services/auth_service.py
    - backend/app/services/email_service.py
    - backend/app/schemas/auth.py
    - backend/app/seed.py
    - backend/app/main.py
    - frontend/src/App.tsx

key-decisions:
  - "RBAC enforced at APIRouter level via dependencies=[] — never inline if-checks in handlers (PITFALLS C4)"
  - "Admin identity = role==librarian AND email==ADMIN_EMAIL; no separate admin role in DB schema"
  - "forgot-password returns 200 for both known and unknown emails to prevent user enumeration (T-03-04)"
  - "Admin email comparison case-insensitive (.lower()) to avoid seed/login mismatch"
  - "All dev-mode email/seed output via print() not logger.info — Docker log capture requires stdout"

patterns-established:
  - "require_librarian / require_admin: reusable DI callables, import in any router that needs role protection"
  - "Router-level guard: APIRouter(dependencies=[Depends(require_admin)]) covers all routes in that router"
  - "Single-use token pattern: EmailToken with used_at checked before use, set on consumption"

requirements-completed: ["AUTH-03", "AUTH-04"]

# Metrics
duration: 90min
completed: 2026-06-08
---

# Phase 01-03: RBAC, Admin Seed, and Password Reset Summary

**Router-level RBAC (401/403/200), idempotent admin superuser seed, admin-only librarian promotion, and full forgot/reset-password flow with React pages — 51 backend tests passing**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-06-08T00:00:00Z
- **Completed:** 2026-06-08T23:59:00Z
- **Tasks:** 3 (2 TDD auto + 1 human-verify checkpoint)
- **Files modified:** 15

## Accomplishments

- RBAC enforced at the APIRouter level: unauthenticated requests return 401, student tokens return 403, librarian/admin tokens return 200 — zero inline role checks in handlers
- Idempotent admin superuser seeded from ADMIN_EMAIL/ADMIN_PASSWORD on startup; re-runs are no-ops; seed confirmation printed to stdout
- Admin-only POST /api/admin/users/{id}/promote elevates any user to librarian; protected at router level via require_admin
- Full password reset round-trip: forgot-password creates a single-use 1h token, reset-password updates the hash and marks the token used; no user enumeration on forgot-password
- ForgotPassword.tsx and ResetPassword.tsx React pages wired into App.tsx routing

## Task Commits

Each task was committed atomically:

1. **RED-1: failing RBAC + admin promote tests** - `5d60f47` (test)
2. **GREEN-1: RBAC dependencies, admin seed, promote endpoint** - `8572f03` (feat)
3. **RED-2: failing password reset tests** - `1ed0a98` (test)
4. **GREEN-2: password reset flow backend + React** - `17f142d` (feat)
5. **Fix: case-insensitive admin email check + debug print** - `f139d4d` (fix)
6. **Fix: print email links to stdout** - `dbf424c` (fix)

## Files Created/Modified

- `backend/app/dependencies.py` - Added require_librarian and require_admin DI callables; get_current_user loads role from DB (not JWT)
- `backend/app/routers/admin.py` - APIRouter with router-level require_admin guard; POST /users/{id}/promote
- `backend/app/routers/auth.py` - Added POST /forgot-password and POST /reset-password public endpoints
- `backend/app/services/auth_service.py` - promote_user_to_librarian, request_password_reset, reset_password
- `backend/app/services/email_service.py` - send_password_reset_email printing reset link to stdout
- `backend/app/schemas/auth.py` - ForgotPasswordRequest, ResetPasswordRequest schemas
- `backend/app/seed.py` - seed_admin_superuser (idempotent, stdout confirmation)
- `backend/app/main.py` - Included admin router under /api; added seed_admin_superuser to startup hook
- `backend/tests/test_rbac.py` - 401/403/200 assertions for require_librarian-protected route
- `backend/tests/test_admin_promote.py` - Promote endpoint tests (admin 200, non-admin 403, idempotent seed)
- `backend/tests/test_password_reset.py` - forgot-password (known/unknown email), reset (valid, used, expired), login with new password
- `frontend/src/pages/ForgotPassword.tsx` - Email form, POST /auth/forgot-password, success message
- `frontend/src/pages/ResetPassword.tsx` - Token from query param, new password form, POST /auth/reset-password, redirect to /login
- `frontend/src/App.tsx` - Added /forgot-password and /reset-password routes

## Decisions Made

- Router-level RBAC chosen over per-route inline checks to comply with PITFALLS C4 and ensure new routes in a protected router are automatically guarded
- Admin identity resolved at runtime as role==librarian AND email==settings.ADMIN_EMAIL — avoids a separate admin role in the DB schema while keeping v1 simple (single seeded admin)
- Case-insensitive email comparison (.lower()) added as a Rule 1 bug fix — environment ADMIN_EMAIL and user input casing could diverge, causing require_admin to return 403 for a legitimate admin login
- All dev email/seed output written via print() not logger.info — Docker's log capture requires writes to stdout/stderr; logger.info was silent in the running stack

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Case-insensitive admin email comparison**
- **Found during:** Task 1 (GREEN-1) — detected during Docker stack testing at human checkpoint
- **Issue:** require_admin compared current_user.email == settings.ADMIN_EMAIL with case-sensitive string equality; if the user registered with a different casing than the env var, the admin check returned False and the correct admin received 403
- **Fix:** Added .lower() to both sides of the comparison in require_admin
- **Files modified:** backend/app/dependencies.py
- **Verification:** Admin receives 200 on promote endpoint in running Docker stack; 51 tests pass
- **Committed in:** f139d4d

**2. [Rule 1 - Bug] Print email/seed logs to stdout instead of logger.info**
- **Found during:** Task 1 (GREEN-1) and Task 2 (GREEN-2) — Docker stack showed no seed or reset-link output in logs
- **Issue:** logger.info was silent in the Docker container log stream; the admin seed confirmation and password reset link URL were invisible, making dev/test verification impossible
- **Fix:** Replaced logger.info calls with print() in seed.py and email_service.py
- **Files modified:** backend/app/seed.py, backend/app/services/email_service.py
- **Verification:** Docker compose logs show "[seed] Seeded admin superuser" on startup and reset link on forgot-password call
- **Committed in:** dbf424c

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both fixes required for correct operation in the Docker stack. No scope creep.

## Issues Encountered

- Docker log capture required print() rather than logger.info — resolved via Rule 1 auto-fix (devf424c)
- Admin email case mismatch between env var and registered user — resolved via Rule 1 auto-fix (f139d4d)

## User Setup Required

None - no external service configuration required. Password reset links print to stdout (Docker logs) in dev mode; real SMTP delivery is Phase 4.

## Next Phase Readiness

- require_librarian and require_admin are import-ready for all Phase 2+ routers
- Admin superuser is seeded; can promote accounts to librarian via POST /api/admin/users/{id}/promote
- Password reset flow is complete and tested end-to-end
- 51 backend tests passing across all Plan 01 tests
- No blockers for Phase 2 (catalog management)

---
*Phase: 01-foundation-auth*
*Completed: 2026-06-08*
