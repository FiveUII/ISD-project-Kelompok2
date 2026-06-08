# Project Research Summary

**Project:** Library Management System
**Domain:** Web-based institutional library management (school/university)
**Researched:** 2026-06-08
**Confidence:** MEDIUM-HIGH

---

## Executive Summary

This is a well-understood domain with 30+ years of established practice. A school library system centers on two workflows: catalog management (librarians add/edit books) and circulation (checkout, return, overdue tracking, fines). Both are straightforward CRUD with a state machine layered on top. The recommended approach is a three-tier architecture: React SPA, FastAPI REST backend, PostgreSQL, containerized with Docker Compose. No exotic patterns are needed. The biggest risk is schema design: the Book/Copy distinction must be established from day one, as conflating them into a single table requires destructive surgery once loan data exists.

The stack is well-validated. FastAPI 0.136+ with SQLAlchemy 2.0 async, PyJWT + pwdlib/Argon2 for auth, TanStack Query + Zustand on the frontend, and APScheduler for scheduled notifications, all confirmed from official documentation. The only deliberate deviation from the default FastAPI tutorial is using SQLAlchemy 2.0 directly rather than SQLModel, because SQLModel async support lags. This trade-off is worth making given that async DB access is required for a production system handling concurrent checkouts.

The primary risks are architectural (Book/Copy conflation, loan status as a boolean, hardcoded fine rates) and operational (email duplicate sends, scheduler running in multiple workers, Docker DB readiness). All are avoidable with correct schema design in Phase 1 and a notifications idempotency table in the notifications phase. The v1 scope is achievable: auth, catalog, borrowing, fines, and email notifications. Reservations/holds, analytics, and self-service renewals are deferred to v2.

---

## Key Findings

### Recommended Stack

The backend is Python 3.11+ / FastAPI 0.136+ on Uvicorn with SQLAlchemy 2.0 async (not SQLModel) connecting to PostgreSQL 16 via asyncpg. Alembic handles all migrations. Auth uses PyJWT 2.x and pwdlib[argon2]. External HTTP (Open Library ISBN lookup) uses httpx async. Scheduled notifications run via APScheduler in a dedicated container, not Celery. The frontend is React 18 + Vite 5, with TanStack Query v5 for server state, Zustand 4 for auth/session state, Axios for HTTP, and Tailwind CSS + shadcn/ui for UI. All services run under Docker Compose with Nginx serving the React static build and proxying /api/* to FastAPI.

**Core technologies:**
- FastAPI 0.136+ -- async REST framework, built-in OpenAPI docs, native DI for RBAC
- SQLAlchemy 2.0 (not SQLModel) -- mature async support via AsyncSession; SQLModel async was immature as of early 2025
- PostgreSQL 16 -- ACID transactions, native ENUM types, partial unique indexes (critical for preventing double-loans)
- PyJWT + pwdlib[argon2] -- FastAPI official recommendation; python-jose is unmaintained
- TanStack Query v5 + Zustand -- server state vs. client state split; eliminates Redux
- APScheduler (separate container) -- scheduled jobs for nightly overdue/reminder tasks without Celery overhead
- Tailwind CSS + shadcn/ui -- fast admin dashboard UI without MUI bundle weight

### Expected Features

**Must have (table stakes) -- v1:**
- Student catalog search by title, author, ISBN with real-time availability
- Student views: current loans, loan history, outstanding fines
- Librarian catalog CRUD with ISBN auto-fetch via Open Library API
- Checkout and return workflow (librarian-initiated)
- Due date tracking and overdue detection
- Fine calculation on return; fine ledger with pay/waive by librarian
- Librarian dashboards: active loans, overdue list, student account detail
- Email notifications: due-date reminder (configurable days before) and overdue alert
- Role-based access: student vs. librarian, enforced at API dependency level
- Configurable loan period, fine rate, and reminder window (library_settings table, not hardcoded)

**Should have (v2 differentiators):**
- Book cover images (Open Library cover API -- trivial add-on once catalog is stable)
- Reservation/hold queue with hold-ready notification
- Student renewal requests
- Reporting: most-borrowed books, fine revenue, collection utilization
- Bulk ISBN import (CSV) and exportable loan history (PDF/CSV)

**Defer (v2+/never):**
- Student self-checkout, barcode/RFID scanning
- Payment gateway for fines (manual librarian recording is sufficient for v1)
- Mobile app, e-books, external system integrations (MARC21, SIP2)
- Multi-branch support, social features (reviews, ratings)

### Architecture Approach

Three-tier: React SPA communicates with a single FastAPI process over REST/JSON. FastAPI handles auth (JWT decode + role check via dependency injection), all CRUD operations, outbound Open Library calls (httpx async), and email dispatch (BackgroundTasks). A separate scheduler container makes an internal HTTP call to /notifications/send-reminders nightly. PostgreSQL is the sole data store; no Redis or message broker needed for v1.

**Major components:**
1. React SPA (Vite) -- catalog browse, loan views, librarian dashboards; role-aware routing with distinct layouts per role
2. FastAPI backend -- auth, CRUD routers (/auth, /catalog, /loans, /fines, /members, /notifications), business logic services
3. PostgreSQL 16 -- User, Book, Copy, Loan, Fine, NotificationLog, LibrarySettings tables
4. Scheduler container (APScheduler or cron) -- daily trigger for overdue checks and reminder emails
5. Nginx -- reverse proxy + static file server for React build
6. Open Library API -- outbound ISBN metadata fetch only (FastAPI side, never from frontend)

**Critical data model decisions:**
- Book (bibliographic record) is separate from Copy (physical item) -- loans attach to Copy, not Book
- Loan.status is an enum: active/overdue/returned/lost -- not a boolean
- Partial unique index on loans(copy_id) WHERE status = active -- prevents double-lending at DB level
- due_date stored as TIMESTAMPTZ not bare DATE; fine calculation in an isolated, tested service function
- library_settings table for fine rate, loan period, reminder window -- no hardcoded constants
- Soft delete (deleted_at) on books, copies, and users -- preserves loan history integrity

### Critical Pitfalls

1. **Book/Copy conflation** -- Never store availability as quantity on the books table. Model Book + Copy as separate tables from day one. Loans reference copy_id. Cannot be retrofitted cheaply after data exists.
2. **Loan status as boolean** -- Use status ENUM(active, overdue, returned, lost) from the start. Adding states later requires data migration and touching every conditional.
3. **Fine calculation without timezone handling** -- Store due_date and returned_at as TIMESTAMPTZ. Extract fine logic into a single tested function. Off-by-one timezone errors generate hard-to-audit student complaints.
4. **Auth guards missing on new routes** -- Apply auth dependencies at the APIRouter level, not per-route. Add tests asserting 401 for unauthenticated requests and 403 for student access to librarian routes.
5. **Email duplicate sends from multi-worker scheduler** -- Run APScheduler as a separate Docker service. Add a NotificationLog table with an idempotency guard (loan_id, notification_type, scheduled_date) before sending any email.

---

## Implications for Roadmap

Based on the feature dependency graph and architecture component dependencies, a 7-phase build order is recommended.

### Phase 1: Foundation and Data Model
**Rationale:** Every downstream phase depends on correct schema and Docker infrastructure. Schema mistakes cannot be fixed cheaply after data exists.
**Delivers:** Docker Compose stack (db + api + frontend containers), FastAPI scaffold, Alembic initialized, User/Book/Copy tables with migrations, library_settings seed data, soft-delete columns, status enums on all entities.
**Addresses:** Prerequisite for all subsequent phases.
**Avoids:** C1 (Book/Copy conflation), M5 (boolean loan status), m2 (hard deletes), m3 (hardcoded settings), M2 (Docker DB readiness with pg_isready healthcheck).

### Phase 2: Auth and RBAC
**Rationale:** Auth must precede all protected endpoints. Cannot be bolted on later without touching every route.
**Delivers:** /auth/login (JWT issuance), /auth/register, /auth/me, get_current_user dependency, require_librarian dependency at router level, role permission matrix enforced end-to-end.
**Uses:** PyJWT 2.x, pwdlib[argon2], FastAPI OAuth2 scopes pattern.
**Avoids:** C4 (missing auth guards, inline role checks, JWT secret committed to git).

### Phase 3: Catalog Management (Librarian)
**Rationale:** Loan records reference copies which reference books -- catalog data must exist before any borrowing phase can be built or tested.
**Delivers:** /catalog/books CRUD (manual entry + ISBN auto-fetch), /catalog/copies CRUD, Open Library httpx integration with 3-second timeout + manual fallback, librarian catalog admin UI.
**Uses:** httpx async, Open Library API (/isbn/{isbn}.json).
**Avoids:** M4 (blocking ISBN call), Anti-Pattern 5 (never call Open Library from frontend).

### Phase 4: Catalog Search and Availability (Student)
**Rationale:** Students need search before any self-service feature can be demonstrated. Distinct layout from librarian UI.
**Delivers:** /catalog/books GET with full-text search + availability count, student search UI, distinct student layout.
**Uses:** PostgreSQL tsvector GIN index (not ILIKE), React + TanStack Query.
**Avoids:** M1 (ILIKE full-table scan), m1 (librarian vocabulary surfaced in student UI).

### Phase 5: Loans -- Checkout, Return, Loan History
**Rationale:** Core circulation workflow. Depends on catalog (copies must exist) and auth (librarian-only checkout endpoints).
**Delivers:** /loans POST (checkout), /loans/{id}/return, /loans GET (librarian), /loans/my (student), fine amount calculated on return, checkout/return forms, loan dashboards for both roles.
**Uses:** Partial unique index for double-loan prevention, TIMESTAMPTZ fine calculation service function with unit tests.
**Avoids:** C2 (timezone fine arithmetic), m4 (stale availability -- server-side copy status check at loan creation).

### Phase 6: Fines Ledger
**Rationale:** Fines are a side-effect of loan returns -- the Loan table must be stable before the Fine table is meaningful.
**Delivers:** Fine table + migration, /fines GET, /fines/{id}/pay, /fines/{id}/waive, student fine balance view, librarian fine ledger.
**Uses:** Fine status enum (pending/paid/waived), amount_per_day stored on fine row (rate-change-safe).
**Avoids:** Anti-Pattern 2 (recalculating fines on every query -- lock amount at return time).

### Phase 7: Email Notifications
**Rationale:** Last because it depends on stable loan/fine data model and introduces external SMTP infrastructure.
**Delivers:** NotificationLog table with idempotency guard, /notifications/send-reminders and /notifications/send-overdue endpoints, FastAPI BackgroundTasks email dispatch, dedicated scheduler container, transactional email service configuration, Mailpit for local dev.
**Uses:** APScheduler in separate Docker service, FastAPI BackgroundTasks, aiosmtplib or Resend SDK.
**Avoids:** C3 (fire-and-forget email), M3 (duplicate sends from multi-worker scheduler), m5 (email spam -- use transactional email service for SPF/DKIM).

### Phase Ordering Rationale

- Schema-first: Phase 1 sets the data model; retrofitting Book/Copy separation or enum status after data exists is expensive.
- Auth before features: Every Phase 3+ endpoint is protected. Auth must be solid before writing business logic on top.
- Catalog before loans: Loans reference copies which reference books. The FK chain is a hard dependency.
- Loans before fines: Fines are created as a side-effect of loan returns.
- Notifications last: Entirely decoupled from core functionality; delaying avoids SMTP complexity before the core is stable.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 7 (Notifications):** APScheduler + FastAPI integration pattern (separate container vs. database lock) needs a working example verified. Confirm transactional email provider selection before planning.
- **Phase 3 (Open Library):** Confirm /isbn/{isbn}.json response shape and author resolution secondary call before building. Confirm rate limits.
- **Phase 2 (Auth):** Verify current SQLModel async maturity before committing to SQLAlchemy 2.0.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Docker Compose + FastAPI scaffold + Alembic is HIGH-confidence, verified from official docs.
- **Phase 4 (Search):** PostgreSQL full-text search with tsvector + GIN index is a standard, well-documented pattern.
- **Phase 5 (Loans):** CRUD + state machine on well-defined schema. Standard FastAPI patterns apply.
- **Phase 6 (Fines):** Simple CRUD on Fine table with no novel patterns.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | FastAPI version, auth patterns, Docker deployment verified from official docs (HIGH). SQLAlchemy vs. SQLModel async, TanStack Query v5, APScheduler integration based on training data (MEDIUM). |
| Features | HIGH | Library management is a mature domain. Table stakes features stable across 30+ years of LMS implementations. |
| Architecture | HIGH/MEDIUM | FastAPI router structure, RBAC via DI, BackgroundTasks for email verified from official docs. Book/Copy separation and partial unique index are established domain knowledge. |
| Pitfalls | MEDIUM | Well-established patterns from FastAPI, PostgreSQL, and LMS communities. FastAPI security advisories not verified against current docs. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **SQLModel async maturity:** Recommended SQLAlchemy 2.0 based on training data from early 2025. Verify current SQLModel async docs before Phase 1 sprint.
- **Open Library API rate limits and response shape:** Not verified from live docs. Test the ISBN endpoint early in Phase 3. Prepare Google Books API as fallback.
- **APScheduler + FastAPI integration:** Separate-container pattern is architecturally clean but needs a working example confirmed before Phase 7 planning.
- **Transactional email provider:** Confirm Resend vs. SendGrid vs. SES availability, free tier limits, and Python SDK quality before Phase 7.
- **Fine accrual policy:** Whether fines accrue on weekends and public holidays is a policy decision that must be confirmed with stakeholders before Phase 5.

---

## Sources

### Primary (HIGH confidence)
- FastAPI official docs (fetched 2026-06-08): release notes (0.136.3), JWT/OAuth2 auth, OAuth2 scopes, router structure, pagination, CORS, BackgroundTasks, Docker deployment, testing -- https://fastapi.tiangolo.com
- FastAPI SQL databases / SQLModel guidance: https://fastapi.tiangolo.com/tutorial/sql-databases/

### Secondary (MEDIUM confidence)
- Open Library Books API -- ISBN endpoint and cover URL pattern -- https://openlibrary.org/developers/api
- PostgreSQL full-text search (tsvector, GIN index) -- https://www.postgresql.org/docs/current/textsearch.html
- Docker Compose healthchecks (pg_isready) -- https://docs.docker.com/compose/compose-file/05-services/#healthcheck
- APScheduler multi-instance warning -- https://apscheduler.readthedocs.io/en/stable/userguide.html
- LMS domain patterns (Koha, Evergreen, Destiny, Follett Aspen) -- feature expectations and Book/Copy schema design

### Tertiary (training data -- verify before use)
- SQLAlchemy 2.0 async vs. SQLModel async maturity comparison
- TanStack Query v5 API specifics
- APScheduler + FastAPI startup integration pattern
- Resend Python SDK availability and free tier limits

---
*Research completed: 2026-06-08*
*Ready for roadmap: yes*
