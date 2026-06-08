# Phase 1: Foundation & Auth - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the complete Docker Compose stack (FastAPI + React + PostgreSQL + Nginx), the foundational data model (User, Book, Copy tables with correct schema), and a working role-based authentication system (JWT login, student self-registration with email verification, password reset, and librarian role promotion by admin).

This phase does NOT deliver any catalog, loan, or notification features — those are Phases 2–4.

</domain>

<decisions>
## Implementation Decisions

### Account Creation Model
- **D-01:** Students self-register via a public `/auth/register` endpoint (email + password). Email verification required before first login — blocked, not warned.
- **D-02:** [informational] Librarians use the same self-register flow as students. After registering, their role is `student` by default.
- **D-03:** A seeded admin superuser (credentials from environment variables) can promote any registered account to `librarian` role via a protected `/admin/users/{id}/promote` endpoint. This superuser is created by the DB seed on first startup — not a normal user.
- **D-04:** [informational] No account deactivation in v1. Accounts are permanent once created.
- **D-05:** No separate admin UI for role promotion — API endpoint only (Swagger / curl). Librarian promotion is an infrequent operation.

### Docker Development Setup
- **D-06:** Dev uses `docker-compose.yml` (base config) + `docker-compose.override.yml` (auto-loaded by Docker Compose for local dev). No separate dev/prod files to keep duplication minimal.
- **D-07:** Both FastAPI and React have hot reload in dev: FastAPI runs with `uvicorn --reload` and a source volume mount; React runs the Vite dev server (HMR) proxied through Nginx (or directly on port 5173 in dev).
- **D-08:** Production compose uses the base `docker-compose.yml` only — React built as static files, FastAPI runs without `--reload`.

### Claude's Discretion
- **Admin superuser seeding:** Admin account seeded via env vars (`ADMIN_EMAIL`, `ADMIN_PASSWORD`) on first startup. If admin already exists in DB, seed is a no-op. This is the simplest way to bootstrap librarian role promotion without a chicken-and-egg problem.
- **Docker structure:** Single base + override pattern chosen over separate dev/prod files — less duplication, matches official Docker Compose documentation guidance.
- **JWT storage:** Access token in `localStorage` (simpler for a school intranet SPA; no cross-site attack surface in practice). Refresh token not implemented in v1 — access token TTL set to 24h. Can revisit in v2.
- **JWT lifetime:** 24-hour access tokens. No refresh token in v1.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Core value, constraints, tech stack decisions, out-of-scope boundaries
- `.planning/REQUIREMENTS.md` — AUTH-01 through AUTH-04 are the requirements for this phase (traceability table maps them to Phase 1)

### Research Findings
- `.planning/research/STACK.md` — Technology choices with versions: FastAPI 0.136+, SQLAlchemy 2.0 async (NOT SQLModel), PyJWT 2.x + pwdlib[argon2], React 18 + Vite 5, TanStack Query v5, Zustand 4, Tailwind + shadcn/ui
- `.planning/research/ARCHITECTURE.md` — Data model decisions: Book/Copy separation, User/role model, RBAC via FastAPI DI (not middleware), partial unique indexes, soft-delete columns. Docker Compose structure (db + api + frontend + nginx + scheduler services)
- `.planning/research/PITFALLS.md` — Critical phase 1 pitfalls: Docker DB readiness (`depends_on` + healthcheck), auth guards at router level (not per-route), JWT secret in env vars (never committed)
- `.planning/research/SUMMARY.md` — Executive summary and build-order rationale

### Roadmap
- `.planning/ROADMAP.md` §Phase 1 — Success criteria and requirement list for this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. No existing code to reuse.

### Established Patterns
- None yet — Phase 1 establishes all foundational patterns that subsequent phases will follow.

### Integration Points
- Phase 1 output is the foundation for all downstream phases:
  - Book/Copy schema (Phase 2 catalog builds on top)
  - Auth middleware and RBAC dependencies (Phases 2–4 protected endpoints all use these)
  - Docker Compose services (all phases use the same stack)

</code_context>

<specifics>
## Specific Ideas

- Hot reload in dev: Vite HMR for React, uvicorn `--reload` for FastAPI — both confirmed desirable
- Admin superuser seeded via env vars (`ADMIN_EMAIL`, `ADMIN_PASSWORD`) — no hardcoded credentials
- Email verification is strict: login blocked (not just warned) until email is verified

</specifics>

<deferred>
## Deferred Ideas

- Account deactivation / suspension — user confirmed out of scope for v1
- Refresh token / silent re-auth — deferred to v2; 24h access token TTL is sufficient for v1
- Admin UI for role management — API-only in v1; a UI panel could be added in v2
- Multi-factor authentication — out of scope for v1

</deferred>

---

*Phase: 1-Foundation & Auth*
*Context gathered: 2026-06-08*
