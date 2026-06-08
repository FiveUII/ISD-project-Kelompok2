# Phase 1: Foundation & Auth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 1-Foundation & Auth
**Areas discussed:** Account creation model, Docker dev setup

---

## Account creation model

| Option | Description | Selected |
|--------|-------------|----------|
| Seeded in DB at startup | Default librarian account created via seed script / env vars | |
| Admin role creates them | Separate admin superuser can create librarian accounts through API or UI | |
| Librarians register like students | Same self-register flow, then an admin promotes to librarian role | ✓ |

**User's choice:** Librarians register like students (same self-register flow, role promoted afterward)

### Who promotes to librarian?

| Option | Description | Selected |
|--------|-------------|----------|
| Another librarian via the UI | Any existing librarian can promote accounts | |
| Admin superuser role | Seeded admin handles role promotion; librarians can't self-promote | |
| You decide | Claude picks the simpler option | ✓ |

**User's choice:** Deferred to Claude

### Account deactivation?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — librarian can suspend accounts | Useful for students who leave or have unpaid fines | |
| No — accounts are permanent in v1 | Keep it simple; account management is v2 | ✓ |

**User's choice:** No account deactivation in v1

---

## Docker dev setup

### Dev environment structure

| Option | Description | Selected |
|--------|-------------|----------|
| Single docker-compose.yml + override file | Base config + docker-compose.override.yml for dev | |
| Separate dev and prod files | docker-compose.dev.yml and docker-compose.prod.yml | |
| You decide | Claude picks the most practical setup | ✓ |

**User's choice:** Deferred to Claude

### Hot reload?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes for both | FastAPI uvicorn --reload + React Vite HMR | ✓ |
| FastAPI only | Backend hot reload, React served as static build | |
| No — rebuild to test | Full rebuild for all changes | |

**User's choice:** Hot reload for both FastAPI and React in development

---

## Claude's Discretion

- **Docker structure:** Single base + override pattern chosen (less duplication, standard Docker Compose practice)
- **Admin superuser:** Seeded via `ADMIN_EMAIL` / `ADMIN_PASSWORD` env vars on first startup; no-op if admin already exists
- **JWT storage:** localStorage (school intranet SPA; XSS risk acceptable); 24h access token TTL; no refresh token in v1
- **Librarian promotion:** API-only (`/admin/users/{id}/promote`), no UI

## Deferred Ideas

- Account deactivation — user confirmed out of scope for v1
- Refresh token / silent re-auth — 24h TTL sufficient for v1; revisit in v2
- Admin UI for role management — API-only in v1
