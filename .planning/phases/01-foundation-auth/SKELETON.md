# Walking Skeleton — Library Management System

**Phase:** 1
**Generated:** 2026-06-08

## Capability Proven End-to-End

A visitor loads the React app at `http://localhost`, the page calls `GET /api/health/db`, FastAPI executes a real query against PostgreSQL (reading the seeded `library_settings` row), and the page renders the returned `loan_period_days` value — exercising Nginx → React → FastAPI → SQLAlchemy async → PostgreSQL through Docker Compose.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI 0.136+ on Uvicorn (Python 3.11+) | Async-first, native DI for RBAC, auto OpenAPI docs (STACK.md) |
| ORM / DB driver | SQLAlchemy 2.0 async (`AsyncSession`, `AsyncEngine`) + asyncpg — NOT SQLModel | SQLModel async maturity lags (CONTEXT.md, STACK.md); SQLAlchemy 2.0 async is battle-tested |
| Migrations | Alembic 1.13+ (async env.py) | Standard for SQLAlchemy; never use `create_all()` past initial dev (ARCHITECTURE.md) |
| Database | PostgreSQL 16 | Project constraint; partial unique indexes, native enums, TIMESTAMPTZ |
| Auth (later slices) | PyJWT 2.x + pwdlib[argon2], JWT in localStorage, 24h TTL, no refresh | CONTEXT.md D (Claude's Discretion); OWASP Argon2 |
| RBAC | FastAPI dependency injection at APIRouter level (`dependencies=[Depends(require_librarian)]`) — NOT middleware, NOT per-route inline checks | ARCHITECTURE.md RBAC; PITFALLS C4 |
| Frontend | React 18 + Vite 5 + React Router 6, TanStack Query v5, Zustand 4 (persisted to localStorage), Axios, Tailwind 3 + shadcn/ui | STACK.md |
| Reverse proxy | Nginx 1.25+ serves React build + proxies `/api/*` to backend | STACK.md; avoids frontend CORS in prod |
| Dev workflow | `docker-compose.yml` (base) + `docker-compose.override.yml` (auto-loaded dev): uvicorn `--reload` + source volume mount; Vite HMR | CONTEXT.md D-06, D-07 |
| DB readiness | `pg_isready` healthcheck + `depends_on: condition: service_healthy` | PITFALLS M2 |
| Directory layout | `backend/app/{routers,models,schemas,services,core}` + `frontend/src/{pages,components,lib,store}` | STACK.md router organization |

## Stack Touched in Phase 1 (Plan 01)

- [x] Project scaffold (FastAPI app, Vite React app, pytest, Docker Compose)
- [x] Routing — `GET /api/health` (liveness) and `GET /api/health/db` (real DB read)
- [x] Database — real read (`library_settings` seed) AND real write (Alembic migration creates tables; seed inserts row)
- [x] UI — React landing page calls `/api/health/db` via Axios + TanStack Query and renders the value
- [x] Deployment — full stack runs with a single `docker compose up`; all healthchecks pass

## Out of Scope (Deferred to Later Slices)

- Authentication, registration, login, JWT (Plan 02)
- Email verification, password reset, RBAC enforcement, admin seed, role promotion (Plan 03)
- Catalog CRUD, ISBN lookup, search (Phase 2)
- Loans, fines, notifications (Phases 3–4)
- shadcn/ui component library beyond Tailwind base setup (introduced as needed by auth UI in Plan 02)

## Subsequent Slice Plan

Each later plan/phase adds one vertical slice without altering the architectural decisions above:

- Plan 02 (Phase 1): A visitor can register, verify email, and log in — receiving a JWT persisted across sessions.
- Plan 03 (Phase 1): RBAC enforced at the API level; admin superuser seeded; librarian promotion + password reset.
- Phase 2: Librarians manage the catalog; students search and see availability.
- Phase 3: Checkout, return, due-date tracking, loan dashboards.
- Phase 4: Fine ledger and automated email notifications.
