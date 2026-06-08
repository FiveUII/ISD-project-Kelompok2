---
phase: 01-foundation-auth
plan: 02
subsystem: auth
tags: [fastapi, pyjwt, argon2, sqlalchemy, react, zustand, email-verification, jwt]

# Dependency graph
requires:
  - 01-01 (AsyncSession get_db, User model, Base, settings.JWT_SECRET)
provides:
  - Argon2 password hashing + PyJWT 24h encode/decode (app.core.security)
  - EmailToken model (verify/reset single-use tokens, 24h TTL)
  - auth_service: register_user, verify_email_token, authenticate_user
  - email_service: send_verification_email (dev: logs link; Phase 4: SMTP)
  - get_current_user FastAPI dependency (Bearer JWT → DB user load)
  - POST /api/auth/register, GET /api/auth/verify-email, POST /api/auth/login, GET /api/auth/me
  - Alembic migration 0002_email_tokens.py
  - React: Register, Login, VerifyEmail pages
  - Zustand useAuthStore persisted to localStorage (token + user)
  - apiClient interceptor attaching Bearer token from auth store
affects: [03-password-reset, 04-catalog, all protected endpoints (use get_current_user)]

# Tech tracking
tech-stack:
  added:
    - PyJWT 2.13.0 (JWT encode/decode, HS256)
    - pwdlib[argon2] 0.3.0 (Argon2id password hashing via PasswordHash.recommended())
    - pydantic[email] (email-validator for EmailStr — added to requirements.txt)
  patterns:
    - Argon2id via PasswordHash.recommended() for all password hashing
    - JWT sub = str(user.id); role is informational only — get_current_user always loads from DB
    - EmailToken single-use: used_at set on consume; second use → 400
    - Login blocked (403) until is_email_verified=True (D-01)
    - Zustand persist middleware → localStorage key "lms-auth"
    - Auth store accessed via useAuthStore.getState() in Axios interceptor (not React hook)

key-files:
  created:
    - backend/app/core/security.py
    - backend/app/models/email_token.py
    - backend/app/schemas/__init__.py
    - backend/app/schemas/auth.py
    - backend/app/services/__init__.py
    - backend/app/services/auth_service.py
    - backend/app/services/email_service.py
    - backend/app/dependencies.py
    - backend/app/routers/auth.py
    - backend/alembic/versions/0002_email_tokens.py
    - backend/tests/test_auth_register.py
    - backend/tests/test_auth_login.py
    - frontend/src/store/auth.ts
    - frontend/src/pages/Register.tsx
    - frontend/src/pages/Login.tsx
    - frontend/src/pages/VerifyEmail.tsx
  modified:
    - backend/app/main.py (added auth router mount under /api)
    - backend/app/models/__init__.py (added EmailToken import)
    - backend/app/requirements.txt (added pydantic[email])
    - frontend/src/lib/api.ts (interceptor reads from Zustand, not raw localStorage)
    - frontend/src/App.tsx (added /register, /login, /verify-email routes)

key-decisions:
  - "get_current_user loads User from DB by JWT sub claim — role never trusted from token payload (PITFALLS Anti-Pattern 3 / T-02-03)"
  - "Email verification strictly blocks login — 403 returned until is_email_verified=True (D-01 / T-02-04)"
  - "send_verification_email logs the link in dev (no SMTP until Phase 4) — function signature is async and injectable for tests"
  - "Argon2id via PasswordHash.recommended() — OWASP current recommendation (CLAUDE.md / T-02-02)"
  - "JWT lifetime 24h, no refresh token in v1 (D — Claude discretion, CONTEXT.md)"
  - "pydantic[email] added to requirements.txt — EmailStr requires email-validator at runtime"

requirements-completed: [AUTH-01, AUTH-02]

# Metrics
duration: ~90min
completed: 2026-06-08
---

# Phase 01 Plan 02: Auth Vertical Slice Summary

**JWT auth vertical slice: Argon2 register → email verify → 24h JWT login with Zustand localStorage persistence, strict 403 block on unverified login, and role loaded from DB on every request.**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-06-08T00:00:00Z
- **Completed:** 2026-06-08T00:00:00Z
- **Tasks:** 2 (both auto, TDD)
- **Files modified:** 20

## Accomplishments

### Task 1: Security primitives, register + email verification (backend)

- `app/core/security.py`: Argon2id hashing via `pwdlib.PasswordHash.recommended()` + PyJWT 24h encode/decode reading `settings.JWT_SECRET` (never hardcoded — PITFALLS C4)
- `app/models/email_token.py`: `EmailToken` table with user_id FK, unique token (urlsafe random), token_type (verify/reset), expires_at, used_at (single-use enforcement)
- `app/schemas/auth.py`: `RegisterRequest`, `LoginRequest`, `TokenResponse`, `UserResponse` (Pydantic v2)
- `app/services/auth_service.py`: `register_user` (409 on duplicate, Argon2 hash, EmailToken + email log), `verify_email_token` (400 on invalid/used/expired), `authenticate_user` (401/403 gates)
- `app/services/email_service.py`: logs verification URL at INFO level; SMTP wired in Phase 4
- `app/dependencies.py`: `get_current_user` — decodes Bearer JWT, loads User row from DB (role from DB, not token)
- `app/routers/auth.py`: POST /register 201, GET /verify-email 200/400, POST /login 200/401/403, GET /me 200/401
- `alembic/versions/0002_email_tokens.py`: creates email_tokens table (CASCADE from users)

### Task 2: Login (JWT) + /auth/me, React auth UI

- `frontend/src/store/auth.ts`: `useAuthStore` (Zustand `persist` middleware, localStorage key `lms-auth`, `{ token, user, setAuth, logout }`)
- `frontend/src/lib/api.ts`: Axios interceptor reads token from `useAuthStore.getState()` (not raw localStorage hook)
- `frontend/src/pages/Register.tsx`: full_name + email + password form → POST /auth/register → success or error state
- `frontend/src/pages/VerifyEmail.tsx`: reads `token` query param → GET /auth/verify-email → success/error feedback
- `frontend/src/pages/Login.tsx`: POST /auth/login → GET /auth/me → setAuth → redirect to `/`; 403 shows "Please verify your email first"
- `frontend/src/App.tsx`: routes for `/register`, `/login`, `/verify-email`

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED-1 | Failing register + verify tests | 344548b | test_auth_register.py |
| GREEN-1 | Security primitives, register + email verification | c91d177 | security.py, email_token.py, schemas/auth.py, services/auth_service.py, email_service.py, dependencies.py, routers/auth.py, main.py, 0002_email_tokens.py, requirements.txt |
| RED-2 | Login + /me tests | 54ce85c | test_auth_login.py |
| GREEN-2 | React auth UI + Zustand store | 5f67192 | store/auth.ts, lib/api.ts, Register.tsx, Login.tsx, VerifyEmail.tsx, App.tsx |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SQLite timezone-naive datetime comparison**
- **Found during:** Task 1 verification (test_register_creates_email_token, test_verify_email_valid_token)
- **Issue:** aiosqlite returns `datetime` objects without timezone info. Comparing with `datetime.now(timezone.utc)` (timezone-aware) raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
- **Fix:** Added timezone-stripping logic in `auth_service.py` `verify_email_token` (check `expires_at.tzinfo is None` and strip UTC if so), and updated the test assertion to handle naive datetimes from SQLite.
- **Files modified:** `backend/app/services/auth_service.py`, `backend/tests/test_auth_register.py`
- **Impact:** PostgreSQL always returns timezone-aware; only affects the test runner. Production behavior unchanged.

**2. [Rule 3 - Blocking] Missing pydantic[email] dependency**
- **Found during:** Task 1 (collection error on import)
- **Issue:** `pydantic.EmailStr` requires the `email-validator` package. `pydantic>=2.0.0` alone doesn't install it. ImportError at test collection time.
- **Fix:** Changed `requirements.txt` from `pydantic>=2.0.0` to `pydantic[email]>=2.0.0`. Installed `email-validator` locally.
- **Files modified:** `backend/requirements.txt`

**3. [Rule 3 - Blocking] Missing `__init__.py` in schemas/ and services/ directories**
- **Found during:** Task 1 (Python package resolution)
- **Issue:** `backend/app/schemas/` and `backend/app/services/` directories were created without `__init__.py`, causing Python not to recognise them as packages.
- **Fix:** Created `backend/app/schemas/__init__.py` and `backend/app/services/__init__.py`.
- **Files modified:** Two new `__init__.py` files.

**4. [Rule 1 - Bug] Test session override not committing**
- **Found during:** Task 1 (test_verify_email_valid_token assertion failure)
- **Issue:** The `override_get_db` fixture yielded the session but didn't call `await session.commit()`, so DB mutations from route handlers weren't visible to subsequent assertions in the same test.
- **Fix:** Updated `override_get_db` in the test fixture to commit (with rollback on exception), matching the pattern from the real `get_db` dependency.
- **Files modified:** `backend/tests/test_auth_register.py`

---

**Total deviations:** 4 auto-fixed  
**Impact on plan:** All fixes were mandatory for tests to pass. No scope creep; no plan goals changed.

## Verification Results

```
backend $ python -m pytest tests/test_auth_register.py tests/test_auth_login.py -q
18 passed in 1.77s

backend $ python -m pytest -q
34 passed in 1.90s
```

### Acceptance Criteria Check

- `grep -nE "argon2|PasswordHash" backend/app/core/security.py`: PASS (PasswordHash imported, _hasher = PasswordHash.recommended())
- `grep -n "JWT_SECRET" backend/app/core/security.py`: PASS (settings.JWT_SECRET on line 44 and 53)
- `backend/app/routers/auth.py` defines `/register` and `/verify-email`: PASS
- `backend/alembic/versions/0002_email_tokens.py` contains `create_table("email_tokens"`: PASS (line 28)
- `grep -n "is_email_verified" backend/app/services/auth_service.py` login blocked on unverified: PASS (line 125)
- `grep -n "persist" frontend/src/store/auth.ts`: PASS (zustand/middleware persist, line 14 and 32)
- `frontend/src/pages/Login.tsx` references `auth/login`: PASS (line 44)
- `frontend/src/App.tsx` declares routes for `/register`, `/login`, `/verify-email`: PASS (lines 15-17)

## Known Stubs

None — all endpoints are functional. Email delivery is logged (not sent) in development; this is intentional and documented. Phase 4 will wire real SMTP via Resend/aiosmtplib.

## Threat Flags

No new security-relevant surface beyond what the plan's threat model covers.

All threat model mitigations applied:
- T-02-01: JWT signed HS256, `sub` verified against DB on every /me request via get_current_user
- T-02-02: Argon2id via pwdlib; plaintext never stored or logged
- T-02-03: get_current_user loads User row from DB; role claim in JWT ignored for auth decisions
- T-02-04: Login returns 403 (not 401) when is_email_verified is False — strict block (D-01)
- T-02-05: Token is urlsafe_token(32) = 43 chars; single-use (used_at set on consume); 24h expiry
- T-02-06: Accepted — v1 school intranet

## Next Phase Readiness

- `get_current_user` dependency is in `app/dependencies.py` — all Plan 03 protected routes import it
- `authenticate_user` returns a User with `role` from DB — Plan 03 RBAC can add `require_librarian` on top
- `EmailToken` model with `token_type="reset"` is ready for Plan 03 password reset (no migration needed)
- All 34 backend tests pass (18 new auth tests + 16 from Plan 01)
- No blockers for Phase 01 Plan 03

---
*Phase: 01-foundation-auth*
*Completed: 2026-06-08*
