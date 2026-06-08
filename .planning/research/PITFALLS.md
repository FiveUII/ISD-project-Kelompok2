# Domain Pitfalls: Library Management System

**Domain:** Web-based Library Management System (FastAPI + React + PostgreSQL + Docker)
**Researched:** 2026-06-08
**Confidence:** MEDIUM — based on training data (cutoff Aug 2025); WebSearch/Bash unavailable during this research session. Patterns are well-established; verify FastAPI-specific security advisories before Phase 3.

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or production outages.

---

### Pitfall C1: Conflating Books with Copies (The Single-Record Trap)

**What goes wrong:**
The schema stores one row per `Book` (title + ISBN) and adds an `available: bool` or `quantity: int` field. This breaks the moment a library has more than one physical copy of the same title, or needs to track which specific copy (barcode/accession number) was borrowed by whom.

**Why it happens:**
Early prototypes model what a catalog *looks like* (one entry per title) rather than what circulation *needs* (one record per physical item).

**Consequences:**
- Cannot distinguish "Copy A is overdue with Alice" from "Copy B is on the shelf"
- Returning one copy of a two-copy title is ambiguous
- Barcode/accession-number scanning (even manual entry) is impossible
- Reports on individual item condition, damage, or loss cannot be produced
- Requires a destructive schema migration to fix after data exists

**Prevention:**
Model with two entities from day one:
- `Book` — bibliographic record (ISBN, title, author, publisher, cover image). One row per unique edition.
- `BookCopy` — physical item (barcode/accession number, condition, acquired date, FK to Book). One row per physical item.
- `Loan` — FK to `BookCopy`, not to `Book`.

Availability is then `SELECT COUNT(*) FROM book_copy WHERE book_id = X AND status = 'available'`, not a denormalized column.

**Warning signs:**
- Any column named `available`, `quantity`, or `copies_available` on the `books` table
- Loans table with `book_id` instead of `copy_id`

**Phase:** Address in Phase 1 (data modeling / database schema). Cannot be retrofitted cheaply.

---

### Pitfall C2: Storing Due Dates as Date-Only, Then Calculating Fines with Naive Datetime Arithmetic

**What goes wrong:**
`due_date` is stored as `DATE` (no time, no timezone). Fine calculation runs as `(today - due_date).days * rate`. This is correct most of the time but silently wrong in these cases:

1. **Timezone mismatch:** The database server, application server, and user browser may be in different timezones. A book returned at 23:58 server-local-time on the due date may be flagged overdue if the scheduler runs in UTC+0 and the due date was set in UTC+8.
2. **Grace period confusion:** "Due by end of day" is ambiguous. If the system sets `due_date = today + 14` (a `DATE`) but the fine job runs at midnight, a student returning at 11 PM local time is charged a day's fine.
3. **Holiday/weekend handling:** Fine accumulation over weekends or public holidays is a policy decision that gets hard-coded as "always accrue" with no config.
4. **Fine on the return date:** Returning on the exact due date should incur zero days of fine, but `(return_date - due_date).days` gives 0 only if the dates match exactly — off-by-one errors appear when mixing `DATE` and `DATETIME` types.

**Consequences:**
- Student complaints that are hard to audit because there is no timestamp trail
- Inconsistent fines depending on which timezone the scheduler runs in
- Manual corrections become the norm, undermining the system's value

**Prevention:**
- Store `due_date` as `TIMESTAMPTZ` (timestamp with time zone) in PostgreSQL, always in UTC
- Define a library-local timezone in application config; translate to/from UTC at the boundary
- Store `returned_at` as `TIMESTAMPTZ` on the Loan record
- Fine = `MAX(0, (returned_at_utc.date() - due_date_utc.date()).days) * rate`  — compare date parts after converting to library-local timezone
- Extract fine calculation into a single tested function; write unit tests covering: same-day return, return one minute after midnight, return on a public holiday, partial-day scenarios
- Store fine as a calculated + confirmed value, not just a live computation — freeze it at return time

**Warning signs:**
- `due_date DATE` column with no timezone config
- Fine calculation inline in the route handler rather than in an isolated service function
- No unit tests for fine calculation edge cases

**Phase:** Address in Phase 2 (borrowing/returns feature). Establish the calculation function with tests before any fine-related UI is built.

---

### Pitfall C3: Email Notification Reliability — Fire-and-Forget Sending

**What goes wrong:**
The application calls `send_email()` directly inside the FastAPI route handler or inside the daily scheduler function. If the SMTP server is slow, unavailable, or rate-limits the request, the HTTP response times out or returns a 500 error. Duplicate sends occur when the scheduler runs twice (e.g., after a server restart) because there is no record of what was already sent.

**Why it happens:**
"Send email" feels like a simple function call. In dev with a local SMTP mock it always works instantly.

**Consequences:**
- Students receive 0 or 10+ copies of the same reminder
- Slow SMTP responses block the scheduler from processing all overdue loans
- No audit trail: impossible to know whether a student was notified before a fine dispute
- Missing emails blamed on the system rather than diagnosable

**Prevention:**
- Use a task queue (Celery + Redis, or APScheduler with database-backed job state) so email sending is decoupled from the scheduler loop
- Before sending, write a `notifications` table row with `status='pending'`; after success update to `status='sent'`. Use this as an idempotency guard: skip if a `sent` record already exists for (loan_id, notification_type, scheduled_date)
- Set per-send timeouts and retry limits on the SMTP client
- Log every send attempt: recipient, template, timestamp, success/failure
- Use a transactional email service (SendGrid, Mailgun, AWS SES) rather than raw SMTP in production — they provide delivery tracking and handle retries at the infrastructure level

**Warning signs:**
- `send_email()` called directly in a route handler
- No `notifications` table or equivalent sent-log
- Scheduler has no idempotency guard (runs, crashes, reruns → duplicates)

**Phase:** Address in Phase 3 (notifications feature). Design the notifications table and idempotency guard before implementing the first email send.

---

### Pitfall C4: FastAPI Auth — Permissive Defaults and Missing Dependency Injection on Routes

**What goes wrong:**
FastAPI's dependency injection makes it easy to add `Depends(get_current_user)` to routes, but easy to forget it too. New routes added during feature development silently have no auth check. Additionally:

1. **Role checks as inline if-statements:** `if current_user.role != "librarian": raise HTTPException(403)` scattered across every route handler instead of a reusable dependency — one missed check = privilege escalation.
2. **Student can access other students' data:** No per-resource ownership check. `GET /loans/{loan_id}` returns the loan to any authenticated user, not just the loan's owner or a librarian.
3. **JWT secret in code or `.env` committed to git:** Exposed secret allows token forgery.
4. **No token expiry / refresh flow:** Tokens are set to non-expiring "for development" and never revisited, or they expire but there is no refresh mechanism, locking users out mid-session.
5. **Password stored in plaintext or with MD5:** Happens when auth is wired up quickly using a tutorial that predates bcrypt as the default.

**Consequences:**
- Any student can view, modify, or delete any other student's loans
- Librarian endpoints accessible to students
- JWT secret leak → all tokens compromised

**Prevention:**
- Define two FastAPI dependencies: `require_librarian = Depends(get_librarian_user)` and `require_student_or_librarian = Depends(get_authenticated_user)`. Apply them at the router level with `APIRouter(dependencies=[...])`, not per-route.
- For per-resource ownership: write a `require_loan_owner_or_librarian(loan_id, current_user)` dependency that fetches the loan and checks ownership in one place.
- Use `python-jose` or `PyJWT` with a short expiry (15–60 min) + refresh token flow. Load the secret from environment variable only.
- Use `passlib[bcrypt]` for password hashing — this is the FastAPI official docs recommendation.
- Add a test that calls every route without auth and asserts 401; add a test that calls librarian routes as a student and asserts 403.

**Warning signs:**
- Role checks written inline in handler bodies
- `GET /loans/{id}` returns data without ownership check
- `.env` with `SECRET_KEY=...` committed to git
- Any route added without a `Depends(...)` on it

**Phase:** Address in Phase 1 (auth scaffolding). Auth architecture cannot be bolted on later without touching every route.

---

## Moderate Pitfalls

---

### Pitfall M1: Catalog Search That Does Not Scale Past 500 Books

**What goes wrong:**
Search is implemented as `WHERE title ILIKE '%query%' OR author ILIKE '%query%'`. This works for a demo but:
- Cannot use a B-tree index (leading wildcard)
- Full table scan on every search
- No relevance ranking (exact match and partial match returned in arbitrary order)
- No stemming, so "computing" does not match "computer"

**Why it happens:**
`ILIKE` is the first thing that works, and the library catalog is rarely large enough during development to feel slow.

**Prevention:**
Use PostgreSQL full-text search from the start:
- Add a `tsvector` generated column on the `books` table: `to_tsvector('english', title || ' ' || author || ' ' || coalesce(description, ''))`
- Index it with `GIN`
- Query with `WHERE search_vector @@ plainto_tsquery('english', :q)`
- For ISBN exact lookup, keep a standard B-tree index on `isbn`

This requires no external service, works in the existing PostgreSQL container, and handles 50,000+ books comfortably. If fuzzy/typo-tolerance is needed later, `pg_trgm` can be layered on without a schema change.

**Warning signs:**
- `ILIKE '%...%'` in the search query
- No GIN index on a tsvector column
- Search tested only with 10–20 books in dev

**Phase:** Address in Phase 1 (catalog feature). Retrofit requires backfilling the generated column and rebuilding the index — low risk but requires a migration run.

---

### Pitfall M2: Docker Compose Service Start-Order and Database Readiness

**What goes wrong:**
`docker-compose.yml` uses `depends_on: db` to start the FastAPI container after PostgreSQL. But `depends_on` only waits for the container to *start*, not for PostgreSQL to be *ready to accept connections*. The FastAPI app starts, tries to connect on its first request, fails with `connection refused`, and either crashes or enters a broken state.

**Why it happens:**
The `depends_on` directive's limitation is not obvious from the docs at a glance.

**Prevention:**
Use a startup health check + retry loop:
- Add `healthcheck` to the `db` service in `docker-compose.yml` using `pg_isready`
- Set `depends_on: db: condition: service_healthy` on the app service
- Add a retry loop in the FastAPI startup event (exponential backoff, 5–10 attempts) as a belt-and-suspenders measure

```yaml
# docker-compose.yml
db:
  image: postgres:16
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U $POSTGRES_USER -d $POSTGRES_DB"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 10s

app:
  depends_on:
    db:
      condition: service_healthy
```

**Warning signs:**
- `depends_on: db` without `condition: service_healthy`
- App crashes on first `docker-compose up` and works on second
- No health check defined for the `db` service

**Phase:** Address in Phase 1 (Docker scaffolding).

---

### Pitfall M3: Scheduler Running Multiple Times in Multi-Worker Deployments

**What goes wrong:**
The daily overdue-fine and reminder scheduler is started inside the FastAPI `startup` event. When the app is run with multiple Uvicorn workers (`--workers 4`) or when docker-compose is scaled (`--scale app=2`), the scheduler starts once per worker. Every overdue job runs N times: N sets of duplicate emails, N fine increments, N database writes.

**Why it happens:**
APScheduler and similar libraries are in-process and have no cross-process coordination by default.

**Prevention:**
- Run the scheduler as a *separate Docker service* (a dedicated `scheduler` container using the same image, started with a different command). This is the cleanest solution and also means scheduler restarts do not affect the web app.
- Alternatively, use a database-backed lock (PostgreSQL advisory lock or a `scheduler_lock` table with a TTL) to elect a single scheduler instance.
- For simplicity at v1 with a single-host deployment, document that the app must run with `--workers 1` until the scheduler is separated.

**Warning signs:**
- Scheduler started in `@app.on_event("startup")`
- No lock mechanism
- Deployment docs say to use multiple workers

**Phase:** Address in Phase 3 (notifications/scheduler). Design the scheduler as a separate service from the first sprint.

---

### Pitfall M4: ISBN Lookup Treated as Synchronous and Blocking

**What goes wrong:**
The "add book by ISBN" feature calls the Open Library API synchronously inside the FastAPI route handler. If Open Library is slow (1–5 seconds), the librarian's browser waits. If it is down, the route returns 500 and the librarian cannot add a book at all — not even manually.

**Prevention:**
- Make ISBN lookup a non-blocking operation: call Open Library with `httpx` (async), set a short timeout (3 seconds), and gracefully fall back to an empty form if the API fails
- The form should always be submittable manually; ISBN lookup is a *convenience pre-fill*, not a gate
- Cache successful ISBN lookups in PostgreSQL (or even in-memory with a TTL) to avoid repeat calls for the same ISBN

**Warning signs:**
- Synchronous `requests.get(open_library_url)` in the route handler
- Route returns 500 when Open Library is unavailable
- No timeout set on the external HTTP call

**Phase:** Address in Phase 2 (catalog management feature).

---

### Pitfall M5: Loan State Machine Implemented as a Boolean Flag

**What goes wrong:**
Loans have a column `returned: bool`. Over time, legitimate states emerge that a boolean cannot represent: active, overdue, returned, lost, renewal-requested, waived. Adding columns (`is_overdue`, `is_lost`, `is_waived`) creates a combinatorial explosion of invalid states (e.g., `returned=True AND is_lost=True`).

**Prevention:**
Use a `status` enum column from day one:
- Valid values: `active`, `overdue`, `returned`, `lost`, `waived`
- Transitions are explicit and validated in the service layer
- Add a `status_updated_at` timestamp for audit purposes

In PostgreSQL, use a native `ENUM` type or a `VARCHAR` with a `CHECK` constraint.

**Warning signs:**
- `returned BOOLEAN` as the only loan status column
- Business logic doing `if not loan.returned and loan.due_date < today: ...` to determine overdue state

**Phase:** Address in Phase 1 (data modeling). Changing a boolean to an enum later requires a data migration and touching every place the boolean is checked.

---

## Minor Pitfalls

---

### Pitfall m1: Student-Facing UI That Exposes Librarian Vocabulary

**What goes wrong:**
The React frontend uses the same component tree and route structure for both students and librarians, just hiding buttons with `{user.role === 'librarian' && <Button>}`. Students see URLs like `/admin/loans`, error messages referencing "accession numbers" or "catalog records", and tables formatted for librarian workflows.

**Why it's a problem:**
Students are the primary self-service users. Confusion at the catalog or availability page increases support burden and reduces adoption.

**Prevention:**
- Create visually distinct layouts for student-facing pages (catalog search, My Loans, notifications) vs. librarian pages (loan management, catalog editing, overdue dashboard)
- Use role-aware routing at the router level, not just conditional rendering inside shared components
- Student-facing language: "Check Out" not "Issue Loan", "Due Back" not "Due Date", "My Books" not "My Loans"

**Warning signs:**
- Single `<App>` component tree with conditional buttons
- Student pages surfacing `/admin/...` URLs
- Internal domain terms in UI labels

**Phase:** Address in Phase 2 (student-facing UI). Establish layout split before building catalog search UI.

---

### Pitfall m2: No Soft-Delete or Deactivation for Books and Students

**What goes wrong:**
A book is physically discarded or a student graduates. The record is hard-deleted. All historical loan records referencing that book or student now have dangling foreign keys — either the delete fails (FK constraint) or cascade deletes wipe loan history.

**Prevention:**
- Add `deleted_at TIMESTAMPTZ NULL` to `books`, `book_copies`, and `users` tables
- Filter all active queries with `WHERE deleted_at IS NULL`
- Preserve historical loan records; they reference the soft-deleted entity but remain valid for audit/reporting

**Warning signs:**
- `DELETE FROM books WHERE id = ?` as the "remove book" implementation
- No `deleted_at` column
- Cascade deletes on `loans` from `books` or `users`

**Phase:** Address in Phase 1 (data modeling).

---

### Pitfall m3: Hardcoded Fine Rate and Loan Period

**What goes wrong:**
Fine rate (e.g., $0.25/day) and loan period (e.g., 14 days) are hardcoded as Python constants or React strings. Different book categories (reference books: 3-day loan, regular: 14-day, journals: 7-day) require code changes and redeployment.

**Prevention:**
- Store `loan_period_days` and `fine_rate_per_day` in a `library_settings` table (or per book-category config)
- Expose a librarian settings page to change these without deployment
- Default values at DB seed time are fine; hardcoding in source is not

**Warning signs:**
- `LOAN_DAYS = 14` as a Python module-level constant
- Fine rate embedded in the fine calculation function body

**Phase:** Address in Phase 1 (data modeling) by creating the settings table, even if the UI is Phase 3.

---

### Pitfall m4: React State Staleness for Real-Time Availability

**What goes wrong:**
A student searches for a book, sees "1 copy available", and clicks "Ask Librarian to Check Out". Meanwhile a librarian checked out the last copy 10 seconds ago. The React state shows stale availability. The student is confused when told the book is actually unavailable.

**Prevention:**
- Availability should be re-fetched at the moment of checkout initiation, not relied upon from a cached search result
- Server-side validation at checkout: if no available copy exists, return HTTP 409 Conflict with a clear message
- Optionally: add a short `stale-while-revalidate` cache (e.g., React Query's `staleTime: 30_000`) so the catalog refreshes quietly in the background

**Warning signs:**
- Checkout form trusts client-side availability data without re-querying
- No server-side availability check at the time of loan creation

**Phase:** Address in Phase 2 (borrowing feature). The server-side check is the critical part; the UI polish is secondary.

---

### Pitfall m5: Emails Flagged as Spam Due to Missing SPF/DKIM Configuration

**What goes wrong:**
The system sends email directly from a generic SMTP server (or via a self-hosted Postfix container). Emails arrive in spam or are silently dropped by Gmail, Outlook, or university mail servers because the sending domain has no SPF record, no DKIM signature, and no DMARC policy.

**Prevention:**
- Use a transactional email service (SendGrid free tier, AWS SES, Mailgun) — they handle SPF/DKIM/DMARC setup and provide delivery dashboards
- For development/testing, use Mailpit or MailHog as a local SMTP catch-all (never sends to real addresses)
- Configure the `From:` address to use a real domain the team controls, not `noreply@localhost`

**Warning signs:**
- SMTP host is `localhost` or a raw IP address in production config
- No SPF/DKIM records for the sending domain
- Emails tested only in development with a local mail catcher

**Phase:** Address in Phase 3 (email notifications). Verify SMTP/delivery configuration before sending to real student emails.

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|---------------|------------|
| Phase 1 | DB schema | Books vs. copies conflation (C1) | Two-table model from day one |
| Phase 1 | DB schema | Boolean loan status (M5) | Use status enum, not `returned: bool` |
| Phase 1 | DB schema | Hard deletes (m2) | Add `deleted_at` to books, copies, users |
| Phase 1 | DB schema | Hardcoded settings (m3) | Create `library_settings` table at seed time |
| Phase 1 | Auth | Missing route-level auth guards (C4) | Router-level `dependencies=[]` pattern |
| Phase 1 | Docker | DB readiness (M2) | Healthcheck + `condition: service_healthy` |
| Phase 2 | Borrowing | Fine timezone/date arithmetic (C2) | `TIMESTAMPTZ` + isolated, tested function |
| Phase 2 | Borrowing | Loan state machine (M5) | Enum status column |
| Phase 2 | Borrowing | Stale availability (m4) | Server-side check at loan-creation time |
| Phase 2 | ISBN lookup | Blocking external API call (M4) | Async with timeout + manual fallback |
| Phase 2 | UI | Librarian vocabulary in student UI (m1) | Distinct layouts per role |
| Phase 3 | Notifications | Duplicate emails from multi-worker scheduler (M3) | Separate scheduler container |
| Phase 3 | Notifications | Fire-and-forget email sending (C3) | Notifications table + idempotency guard |
| Phase 3 | Notifications | Email spam/deliverability (m5) | Transactional email service, SPF/DKIM |
| Phase 3 | Search | ILIKE full-table scan (M1) | PostgreSQL full-text search + GIN index |

---

## Sources

- Confidence is MEDIUM across all findings. These patterns are well-established in the FastAPI, PostgreSQL, and library systems communities based on training data (Aug 2025 cutoff).
- WebSearch and Bash tools were unavailable during this session. Specific FastAPI security advisories and Docker Compose version-specific behavior should be verified against official documentation before implementation.
- FastAPI auth patterns: https://fastapi.tiangolo.com/tutorial/security/
- PostgreSQL full-text search: https://www.postgresql.org/docs/current/textsearch.html
- Docker Compose healthchecks: https://docs.docker.com/compose/compose-file/05-services/#healthcheck
- APScheduler multi-instance warning: https://apscheduler.readthedocs.io/en/stable/userguide.html
