---
phase: 01-foundation-auth
plan: 01
subsystem: infra
tags: [fastapi, sqlalchemy, alembic, postgresql, react, vite, docker, nginx, tanstack-query, axios]

# Dependency graph
requires: []
provides:
  - FastAPI async backend with SQLAlchemy 2.0 AsyncSession and get_db dependency
  - Core data model: User, Book, Copy, LibrarySettings with Book/Copy separation, CopyStatus/UserRole/CopyCondition enums, soft-delete columns
  - Alembic initial migration (0001_initial.py) creating all four tables
  - Seed function inserting a single LibrarySettings row (loan_period_days=14)
  - Health endpoints GET /api/health and GET /api/health/db
  - Docker Compose stack (postgres:16 + backend + frontend/nginx) with pg_isready healthcheck and service_healthy gate
  - React 18 + Vite + TanStack Query landing page rendering loan_period_days from /api/health/db
  - Nginx reverse proxy serving SPA with /api/* proxied to backend:8000
affects: [02-auth, 03-books, 04-loans, all subsequent phases]

# Tech tracking
tech-stack:
  added:
    - FastAPI 0.136.x (ASGI web framework)
    - SQLAlchemy 2.0 async (ORM with AsyncSession/AsyncEngine)
    - asyncpg 0.29+ (async PostgreSQL driver)
    - Alembic 1.13+ (schema migrations)
    - pydantic-settings 2.x (Settings from env)
    - PyJWT 2.x (added to requirements, used in later plans)
    - pwdlib[argon2] (added to requirements, used in later plans)
    - HTTPX 0.27+ (async HTTP client, test client)
    - pytest-asyncio 0.23+ (async test support)
    - aiosqlite (in-memory test DB)
    - React 18 + Vite 5 (frontend)
    - TanStack Query v5 (server state)
    - Zustand 4 (client state, wired for later auth)
    - Axios 1 (HTTP client)
    - React Router 6 (client routing)
    - Tailwind CSS 3 (utility styling)
    - Nginx 1.25 (reverse proxy + SPA static serving)
    - Docker Compose v2 (multi-service orchestration)
  patterns:
    - Book/Copy separation: Book holds bibliographic data; Copy holds physical copy with status enum and FK to Book
    - Soft-delete via nullable deleted_at TIMESTAMPTZ on User, Book, Copy
    - No hardcoded constants — loan_period_days and fine_rate_per_day read from library_settings table
    - pg_isready healthcheck + depends_on service_healthy preventing backend crash-loop on cold start
    - docker-compose.override.yml (dev hot-reload) auto-merged over docker-compose.yml (prod)
    - CORS ALLOWED_ORIGINS explicit list (never wildcard with credentials)
    - Idempotent seed: insert LibrarySettings row only if none exists
    - TanStack Query useQuery wrapping Axios apiClient for data fetching
    - Nginx try_files SPA fallback + /api/* proxy_pass to backend service name

key-files:
  created:
    - backend/requirements.txt
    - backend/app/core/config.py
    - backend/app/core/db.py
    - backend/app/core/enums.py
    - backend/app/models/user.py
    - backend/app/models/book.py
    - backend/app/models/copy.py
    - backend/app/models/library_settings.py
    - backend/app/models/__init__.py
    - backend/app/routers/health.py
    - backend/app/main.py
    - backend/app/seed.py
    - backend/alembic.ini
    - backend/alembic/env.py
    - backend/alembic/versions/0001_initial.py
    - backend/tests/conftest.py
    - backend/tests/test_models.py
    - backend/tests/test_health.py
    - backend/Dockerfile
    - docker-compose.yml
    - docker-compose.override.yml
    - .env.example
    - frontend/Dockerfile
    - frontend/nginx.conf
    - frontend/package.json
    - frontend/vite.config.ts
    - frontend/tailwind.config.js
    - frontend/index.html
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/src/lib/api.ts
    - frontend/src/pages/Landing.tsx
  modified: []

key-decisions:
  - "Book/Copy separation enforced: Book model has no availability columns; Copy holds status enum + book_id FK"
  - "SQLAlchemy 2.0 async chosen over SQLModel due to mature AsyncSession support"
  - "npm install used instead of npm ci in Dockerfiles — no package-lock.json in greenfield setup"
  - "vite.config.ts proxy target set to backend:8000 (Docker service name) not localhost:8000"
  - "aiosqlite used for in-memory test DB so model/health unit tests run without a live Postgres instance"
  - "CORSMiddleware configured with explicit ALLOWED_ORIGINS from settings, never wildcard"

patterns-established:
  - "Book/Copy separation: bibliographic data in Book, physical inventory in Copy with CopyStatus enum"
  - "Soft-delete: deleted_at TIMESTAMPTZ nullable on User/Book/Copy; hard deletes forbidden"
  - "Settings from env: pydantic-settings Settings class; module-level settings singleton"
  - "AsyncSession via get_db FastAPI dependency injected into all DB-touching routes"
  - "Alembic migration for every schema change; no manual DDL"
  - "Docker Compose override pattern: base file for prod, override file for dev hot-reload"
  - "service_healthy gate: backend waits for pg_isready before starting"

requirements-completed: []

# Metrics
duration: ~90min
completed: 2026-06-08
---

# Phase 01 Plan 01: Foundation Walking Skeleton Summary

**FastAPI + SQLAlchemy 2.0 async walking skeleton with Book/Copy-separated data model, Alembic migration, Docker Compose stack with pg_isready gate, and React/Nginx landing page rendering loan_period_days live from PostgreSQL.**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-06-08T00:00:00Z
- **Completed:** 2026-06-08T00:00:00Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 33

## Accomplishments

- Core data model (User, Book, Copy, LibrarySettings) with Book/Copy separation enforced, CopyStatus/UserRole/CopyCondition enums, and soft-delete columns — Alembic initial migration generated and verified
- FastAPI app with health endpoints (/api/health, /api/health/db), Docker Compose stack with postgres:16 healthcheck + service_healthy gate, and Nginx reverse proxy
- React 18 + Vite + TanStack Query landing page confirmed by human checkpoint to render "Loan period: 14 days" fetched live from PostgreSQL through the full Browser → Nginx → FastAPI → SQLAlchemy → PostgreSQL round trip

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend scaffold, core data model, and Alembic migration** - `bbac172` (feat)
2. **Task 2: FastAPI app, health endpoints, and Docker Compose stack** - `ffca4af` (feat)
3. **Fix: npm install instead of npm ci** - `c319eff` (fix)
4. **Fix: vite.config.ts proxy target → backend:8000** - `d501097` (fix)

## Files Created/Modified

- `backend/app/core/db.py` — AsyncEngine, async_session_maker, get_db dependency (AsyncSession)
- `backend/app/core/config.py` — pydantic-settings Settings reading DATABASE_URL, ALLOWED_ORIGINS, JWT_SECRET
- `backend/app/core/enums.py` — UserRole, CopyStatus, CopyCondition string enums
- `backend/app/models/book.py` — Book model (bibliographic, no availability columns — C1)
- `backend/app/models/copy.py` — Copy model (book_id FK, CopyStatus enum, soft-delete)
- `backend/app/models/user.py` — User model (UserRole, soft-delete, email unique+indexed)
- `backend/app/models/library_settings.py` — LibrarySettings (loan_period_days, fine_rate_per_day)
- `backend/app/routers/health.py` — GET /health (liveness) and GET /health/db (reads LibrarySettings)
- `backend/app/main.py` — FastAPI app, CORSMiddleware, router mount at /api, startup seed hook
- `backend/app/seed.py` — Idempotent seed_library_settings inserting default row if none exists
- `backend/alembic/versions/0001_initial.py` — create_table for users, books, copies, library_settings
- `backend/tests/test_models.py` — Model shape tests (Book/Copy separation, enums, soft-delete, columns)
- `backend/tests/test_health.py` — Health endpoint tests (liveness + DB round trip)
- `docker-compose.yml` — pg_isready healthcheck, service_healthy gate, three-service stack
- `docker-compose.override.yml` — Hot-reload dev override (uvicorn --reload + source volume)
- `.env.example` — All required env vars with placeholders; no secrets committed
- `frontend/nginx.conf` — SPA try_files fallback + /api/* proxy_pass to backend:8000
- `frontend/src/pages/Landing.tsx` — useQuery → GET /health/db → renders "Loan period: N days"
- `frontend/src/lib/api.ts` — Axios apiClient with baseURL /api
- `frontend/vite.config.ts` — React plugin + dev proxy /api → backend:8000

## Decisions Made

- **Book/Copy separation:** Book model holds bibliographic data only; Copy holds physical inventory with a status enum. This enforces the architectural rule from PITFALLS C1 — availability is determined by querying Copy rows, never a column on Book.
- **npm install over npm ci:** No package-lock.json existed in this greenfield repo. The frontend Dockerfile was corrected from `npm ci` (which requires a lockfile) to `npm install` to unblock the Docker build.
- **vite.config.ts proxy backend:8000:** The dev proxy was initially set to `localhost:8000` which works on the host but fails inside Docker containers. Corrected to the Docker service name `backend:8000`.
- **aiosqlite for unit tests:** Model and health tests use an in-memory SQLite engine via aiosqlite so they run without a live Postgres container, keeping CI fast.
- **Explicit CORS origins:** CORSMiddleware uses `settings.ALLOWED_ORIGINS` from env — never a wildcard — satisfying the STACK.md CORS gotcha and threat T-01-03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] npm ci → npm install in frontend Dockerfile**
- **Found during:** Task 2 (Docker Compose stack)
- **Issue:** `npm ci` requires a `package-lock.json`; no lockfile existed in the greenfield frontend directory, causing the Docker build to fail.
- **Fix:** Changed `npm ci` to `npm install` in `frontend/Dockerfile` so the build generates the lockfile on first run.
- **Files modified:** `frontend/Dockerfile`
- **Verification:** Docker build succeeded; container started cleanly.
- **Committed in:** `c319eff`

**2. [Rule 1 - Bug] vite.config.ts proxy target localhost → backend:8000**
- **Found during:** Task 2 (Docker Compose stack)
- **Issue:** `vite.config.ts` dev proxy pointed to `localhost:8000`. Inside the Docker network this resolves to the container itself rather than the backend service, causing all /api requests to fail with connection refused.
- **Fix:** Changed proxy target to `http://backend:8000` (Docker service name).
- **Files modified:** `frontend/vite.config.ts`
- **Verification:** `docker compose up --build` succeeded; landing page fetched loan_period_days correctly.
- **Committed in:** `d501097`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes were necessary for a working Docker stack. No scope creep; no plan goals changed.

## Issues Encountered

None beyond the two auto-fixed deviations documented above.

## User Setup Required

None - no external service configuration required.
The `.env.example` file must be copied to `.env` and filled with real values before running `docker compose up`. All required env vars are documented in `.env.example`.

## Known Stubs

None — the landing page wires live data from PostgreSQL via /api/health/db. No placeholder text or hardcoded values flow to the UI.

## Threat Flags

No new security-relevant surface beyond what the plan's threat model covers.

All mitigations in the plan threat register were applied:
- T-01-01: `.env` gitignored; `.env.example` holds placeholders only.
- T-01-02: pg_isready healthcheck + `depends_on: condition: service_healthy` present.
- T-01-03: `ALLOWED_ORIGINS` explicit list in `settings`, never `["*"]`.
- T-01-04: Accepted — /api/health/db returns only non-sensitive loan_period_days.

## Next Phase Readiness

- AsyncSession `get_db` dependency, `Settings`, all models, and Alembic are ready for Plan 02 (auth).
- Docker Compose stack boots cleanly; developers can `docker compose up --build` immediately.
- The core schema (User, Book, Copy, LibrarySettings) is migrated and stable — subsequent plans can add columns via new Alembic revisions.
- `backend/tests/conftest.py` aiosqlite fixture is available for all future unit tests.
- No blockers for Phase 01 Plan 02.

---
*Phase: 01-foundation-auth*
*Completed: 2026-06-08*
