# Architecture Patterns

**Domain:** Web-based Library Management System (school/university)
**Stack:** FastAPI (Python) + React + PostgreSQL + Docker
**Researched:** 2026-06-08
**Confidence:** HIGH (FastAPI/SQLModel official docs) / MEDIUM (schema design, build order — established LMS patterns, no official authoritative source)

---

## Recommended Architecture

Three-tier architecture: React SPA frontend, FastAPI REST backend, PostgreSQL database — all containerised with Docker Compose. A single FastAPI process handles HTTP requests, email background tasks, and Open Library API calls. No separate worker process is needed for v1.

```
Browser (React SPA)
      |
      | HTTPS / JSON (REST)
      v
  FastAPI Backend
  ├── Auth layer      (JWT decode + role check via DI)
  ├── APIRouter: /auth
  ├── APIRouter: /catalog       (books + copies)
  ├── APIRouter: /loans         (checkout / return)
  ├── APIRouter: /members       (student accounts)
  ├── APIRouter: /fines         (fine ledger)
  ├── APIRouter: /notifications (admin trigger)
  ├── BackgroundTasks           (email dispatch, fine recalculation)
  └── httpx (async)             (Open Library API calls)
      |
      | SQLAlchemy / SQLModel
      v
  PostgreSQL
      |
      | (read by FastAPI on startup scheduler / background task)
      v
  Email provider (SMTP / SendGrid)
```

---

## Core Data Models

### Books vs Copies distinction (critical)

A **Book** is a bibliographic record (ISBN, title, author, description). A **Copy** is a physical item on the shelf — one book can have many copies. Loans attach to copies, not books. Availability is a count of copies where `status = 'available'`.

Conflating Book and Copy into one table is the most common LMS schema mistake; it makes multi-copy tracking impossible without schema surgery.

### Entity definitions

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `User` | id, email, full_name, hashed_password, role (enum: student/librarian), is_active, created_at | Single table for both roles; role field gates permissions |
| `Book` | id, isbn (unique), title, author, publisher, publish_year, description, cover_url, total_copies, created_at | Bibliographic record; total_copies is a denormalised count updated on copy create/delete |
| `Copy` | id, book_id (FK), barcode (unique, optional), condition (enum: good/fair/poor), status (enum: available/on_loan/lost/withdrawn), created_at | Each physical item; status is the availability source of truth |
| `Loan` | id, copy_id (FK), user_id (FK), issued_by (FK → User librarian), issued_at, due_date, returned_at (nullable), status (enum: active/returned/overdue) | One row per borrow event; returned_at NULL means still out |
| `Fine` | id, loan_id (FK), user_id (FK), amount_per_day (decimal), total_amount (decimal), reason, issued_at, paid_at (nullable), status (enum: pending/paid/waived) | Created when loan becomes overdue or on return if overdue |

### Relationship map

```
User ──< Loan (as borrower)
User ──< Loan (as issued_by librarian)
User ──< Fine

Book ──< Copy
Copy ──< Loan     (one active loan at a time — enforced via partial unique index)
Loan ──< Fine     (zero or one fine per loan)
```

### PostgreSQL-specific design choices

- **Partial unique index** on Copy: `CREATE UNIQUE INDEX one_active_loan_per_copy ON loans (copy_id) WHERE status = 'active'` — prevents double-lending at the database level.
- **Enum columns** (`role`, `status`) as PostgreSQL native `ENUM` types or `VARCHAR` with a `CHECK` constraint. SQLModel/SQLAlchemy's `Enum` type maps cleanly.
- **Alembic** for schema migrations. Never use `SQLModel.metadata.create_all()` beyond initial dev; use Alembic from the first schema change.
- `due_date` stored as `DATE` not `DATETIME`; simplifies overdue calculation (`today - due_date` in days).
- Fine `amount_per_day` is stored so the librarian can change the rate without retroactively altering closed fines.

---

## API Resource Boundaries

### Router: `/auth`
| Endpoint | Method | Role | Purpose |
|----------|--------|------|---------|
| `/auth/login` | POST | public | Exchange credentials for JWT |
| `/auth/register` | POST | public (or librarian-only) | Create student account |
| `/auth/me` | GET | any authenticated | Return current user profile |

### Router: `/catalog`
| Endpoint | Method | Role | Purpose |
|----------|--------|------|---------|
| `/catalog/books` | GET | public / student | Search books (title, author, ISBN) |
| `/catalog/books/{id}` | GET | public / student | Book detail + copy availability count |
| `/catalog/books` | POST | librarian | Add book manually |
| `/catalog/books/isbn/{isbn}` | POST | librarian | Fetch from Open Library + create book |
| `/catalog/books/{id}` | PATCH | librarian | Edit book metadata |
| `/catalog/books/{id}/copies` | POST | librarian | Add a new physical copy |
| `/catalog/copies/{id}` | PATCH | librarian | Update copy condition or status |

### Router: `/loans`
| Endpoint | Method | Role | Purpose |
|----------|--------|------|---------|
| `/loans` | POST | librarian | Check out a copy to a student |
| `/loans/{id}/return` | POST | librarian | Process a return |
| `/loans` | GET | librarian | List active/overdue loans (filterable) |
| `/loans/my` | GET | student | Student's own loan history |
| `/loans/{id}` | GET | librarian | Single loan detail |

### Router: `/fines`
| Endpoint | Method | Role | Purpose |
|----------|--------|------|---------|
| `/fines` | GET | librarian | All outstanding fines |
| `/fines/my` | GET | student | Student's own fines |
| `/fines/{id}/pay` | POST | librarian | Mark fine as paid |
| `/fines/{id}/waive` | POST | librarian | Waive a fine |

### Router: `/members`
| Endpoint | Method | Role | Purpose |
|----------|--------|------|---------|
| `/members` | GET | librarian | List all student accounts |
| `/members/{id}` | GET | librarian | Student profile + loan/fine summary |
| `/members/{id}` | PATCH | librarian | Edit member details, activate/deactivate |

### Router: `/notifications` (internal trigger, not client-facing)
| Endpoint | Method | Role | Purpose |
|----------|--------|------|---------|
| `/notifications/send-reminders` | POST | librarian / cron | Trigger due-date reminder emails |
| `/notifications/send-overdue` | POST | librarian / cron | Trigger overdue alert emails |

---

## RBAC Structure

Role-based access is enforced through FastAPI dependency injection — not middleware. This keeps the logic explicit and close to each endpoint.

### Implementation pattern (HIGH confidence — from official FastAPI docs)

```
Token (JWT)  →  get_current_user() dependency  →  role check dependency
```

1. `get_current_user` — decodes JWT, loads user from DB, returns `User` object. Raises 401 if token invalid/expired.
2. `require_librarian` — depends on `get_current_user`, raises 403 if `user.role != "librarian"`.
3. `require_active` — depends on `get_current_user`, raises 403 if `user.is_active == False`.

```python
# app/dependencies.py

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    # decode JWT, load from DB, return User
    ...

async def require_librarian(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "librarian":
        raise HTTPException(status_code=403, detail="Librarian role required")
    return current_user
```

Each router that needs protection declares the dependency at the router level:

```python
# app/routers/loans.py
router = APIRouter(
    prefix="/loans",
    tags=["loans"],
    dependencies=[Depends(require_librarian)],  # all loan write endpoints
)
```

Endpoints accessible to students use `Depends(get_current_user)` directly.
Catalog search endpoints are public (no dependency).

### Role permission matrix

| Capability | Student | Librarian |
|-----------|---------|-----------|
| Search catalog | Yes | Yes |
| View book availability | Yes | Yes |
| View own loans | Yes | Yes |
| View own fines | Yes | Yes |
| Check out / return | No | Yes |
| Add / edit books | No | Yes |
| View all loans | No | Yes |
| Manage fines (pay/waive) | No | Yes |
| Manage members | No | Yes |
| Trigger notifications | No | Yes |

---

## Open Library ISBN Lookup — Architecture

### Decision: synchronous HTTP call, not a background job

**Rationale:** The librarian initiates ISBN lookup from a form and waits for the response. The call is fast (< 1 s typical). Making it synchronous produces a simpler UX (instant feedback, errors surface immediately). A background job would require polling or WebSocket for the result, adding complexity with no benefit.

### API endpoint (MEDIUM confidence — Open Library docs partially inaccessible; based on known public API)

```
GET https://openlibrary.org/isbn/{isbn}.json
```

Returns: `title`, `authors` (as `/authors/{id}` references — requires second call to resolve name), `publishers`, `publish_date`, `number_of_pages`, `covers` (integer IDs — cover URL is `https://covers.openlibrary.org/b/id/{id}-L.jpg`).

### Data flow

```
Librarian submits ISBN
        |
POST /catalog/books/isbn/{isbn}
        |
FastAPI → httpx.AsyncClient.get("https://openlibrary.org/isbn/{isbn}.json")
        |
If 200: parse title, publisher, year, cover_id
        |
If authors present: httpx.get("https://openlibrary.org/authors/{author_id}.json")  ← second call
        |
Insert Book record, return to librarian for confirmation/edit
        |
If 404 from OL: return 422 with message "ISBN not found in Open Library"
```

### Implementation notes

- Use `httpx.AsyncClient` (not `requests`) to stay non-blocking inside FastAPI's async event loop.
- Set a timeout of 5 seconds; if Open Library is slow, fail gracefully with a clear error. The librarian can fill in fields manually.
- Do not persist author lookups aggressively — author is a plain `VARCHAR` on Book for v1. A separate `Author` table is a future optimisation.

---

## Email Notification Architecture

### Decision: FastAPI `BackgroundTasks` for v1, not Celery

**Rationale (HIGH confidence — from official FastAPI docs):**

| Concern | BackgroundTasks | Celery + Redis |
|---------|----------------|----------------|
| Complexity | Zero — built-in | Requires Redis + Celery worker container |
| Persistence if crash | Lost | Durable queue |
| Scale | Single process | Distributed |
| Good enough for school LMS? | Yes | Overkill |

For a school library serving hundreds of students, tasks run in-process are perfectly adequate. If the deployment grows to tens of thousands of users, migrating to Celery is a well-understood upgrade path.

### Two notification types

**1. Due-date reminder** — sent 1 day before due_date.

**2. Overdue alert** — sent daily while a loan remains overdue.

### Trigger mechanism

A scheduled endpoint (`POST /notifications/send-reminders`) is called by a Docker `cron` container or a simple Starlette startup scheduler (APScheduler). The endpoint queries for qualifying loans and dispatches emails via `BackgroundTasks`.

```
Docker cron (daily)
        |
POST /notifications/send-reminders  (internal, librarian-auth or internal token)
        |
FastAPI queries: loans WHERE due_date = tomorrow AND status = 'active'
FastAPI queries: loans WHERE due_date < today AND status = 'active'  (overdue)
        |
For each matching loan:
    background_tasks.add_task(send_email, to=user.email, template="reminder"|"overdue")
        |
Response: {"queued": N}  (returned immediately, emails sent after response)
        |
BackgroundTask: SMTP send via smtplib or email library
```

### Email implementation notes

- Use Python's standard `smtplib` or `fastapi-mail` (a thin FastAPI wrapper over `aiosmtpd`/SMTP).
- Store SMTP credentials in environment variables; inject via Docker Compose `env_file`.
- Idempotency: add a `notification_sent_at` timestamp to the Loan model or a separate `NotificationLog` table to prevent duplicate sends on re-trigger.

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| React SPA | All user interaction; renders catalog, loan forms, dashboards | FastAPI (REST over HTTPS) |
| FastAPI API layer | Route handling, auth, request validation, response serialisation | PostgreSQL (via SQLModel), Open Library API (httpx), Email SMTP |
| SQLModel ORM layer | Data access, schema definition, migration target | PostgreSQL |
| PostgreSQL | Authoritative data store | FastAPI only |
| Open Library API | ISBN metadata source | FastAPI (outbound only, no callback) |
| Email SMTP | Email delivery | FastAPI BackgroundTasks (outbound only) |
| Docker Compose | Service orchestration; networking between containers | All services |
| Cron container (or APScheduler) | Daily notification trigger | FastAPI `/notifications` endpoint |

---

## Data Flow

### Search and availability check (student)

```
Student searches "Clean Code"
→ GET /catalog/books?q=Clean+Code
→ FastAPI queries: SELECT books + COUNT(copies WHERE status='available')
→ Returns list with availability count
← React renders results with "2 copies available" badge
```

### Borrow flow (librarian)

```
Librarian scans student ID + copy barcode
→ POST /loans { copy_id, user_id, due_date }
→ FastAPI: check copy.status == 'available', check user.is_active
→ INSERT loan (status=active), UPDATE copy (status=on_loan)
← 201 Created with loan detail
```

### Return flow (librarian)

```
Librarian scans copy barcode
→ POST /loans/{id}/return
→ FastAPI: UPDATE loan (returned_at=now, status=returned)
→ UPDATE copy (status=available)
→ If returned_at > due_date: INSERT fine (amount = days_late * rate)
← 200 OK with fine amount (if any)
```

### Fine calculation

```
Fine amount = (returned_at::date - due_date) * amount_per_day
```

Calculated at return time and persisted. No real-time recalculation needed; the fine is fixed once the book is returned.

For still-overdue loans (not yet returned), the outstanding balance displayed to the librarian is calculated on-the-fly in the query:

```sql
(CURRENT_DATE - due_date) * default_daily_rate AS accrued_fine
```

---

## Suggested Build Order (Component Dependencies)

Dependencies flow strictly top-to-bottom. Do not start a phase until its dependencies are complete.

```
Phase 1: Foundation
  ├── Docker Compose setup (postgres + api + frontend containers)
  ├── FastAPI project scaffold (main.py, router structure, DB connection)
  ├── Alembic initialised
  └── Database: User, Book, Copy tables + migrations
        ↓
Phase 2: Auth + RBAC
  ├── /auth/login → JWT issuance
  ├── get_current_user dependency
  ├── require_librarian dependency
  └── /auth/register + /auth/me
        ↓
Phase 3: Catalog Management (librarian)
  ├── /catalog/books CRUD (manual entry)
  ├── /catalog/copies CRUD
  ├── Open Library ISBN fetch (httpx, synchronous)
  └── React: librarian catalog admin pages
        ↓
Phase 4: Catalog Search (student)
  ├── /catalog/books GET with search + availability count query
  └── React: student search UI + availability display
        ↓
Phase 5: Loans
  ├── Database: Loan table + migration
  ├── /loans POST (checkout), /loans/{id}/return
  ├── /loans GET (librarian view), /loans/my (student)
  └── React: checkout/return forms, loan dashboards
        ↓
Phase 6: Fines
  ├── Database: Fine table + migration
  ├── Fine creation on return (if overdue)
  ├── /fines GET, /fines/{id}/pay, /fines/{id}/waive
  └── React: fine display for students and librarians
        ↓
Phase 7: Email Notifications
  ├── NotificationLog table (idempotency)
  ├── /notifications/send-reminders endpoint
  ├── FastAPI BackgroundTasks email dispatch
  ├── Docker cron container or APScheduler
  └── SMTP configuration via env vars
```

**Ordering rationale:**
- Auth must precede all protected endpoints — every downstream phase depends on JWT/role enforcement.
- Catalog (Phase 3 + 4) precedes Loans because loans reference copies which reference books. Catalog data must exist before you can borrow.
- Loans precede Fines because fines are created as a side-effect of loan returns.
- Notifications are last because they depend on the full loan/fine data model being stable and need SMTP infra that is independent of core functionality.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Book = Copy conflation
**What:** Storing `quantity` as a field on `Book` instead of separate `Copy` rows.
**Why bad:** Makes individual copy tracking (condition, loss status, specific barcode) impossible. Loan history becomes ambiguous ("which copy did you borrow?").
**Instead:** Always use a separate `Copy` table. Even if all copies are identical, each gets a row.

### Anti-Pattern 2: Calculating fine at query time on every request
**What:** No stored fine amount; always compute `(today - due_date) * rate` on the fly.
**Why bad:** Rate can change; historical fines become inconsistent. Reporting is slow on large datasets.
**Instead:** Lock the fine amount on return (or when the fine is formally issued). Store `amount_per_day` on the fine row alongside `total_amount`.

### Anti-Pattern 3: Role stored only in JWT, not verified against DB
**What:** `require_librarian` reads role from JWT payload without hitting the database.
**Why bad:** A deactivated librarian account still has valid tokens until expiry. Role changes take up to token-lifetime to take effect.
**Instead:** `get_current_user` loads the full `User` row from the database on every request. JWT is used only to identify the user (via `sub` claim), not to cache their role. This is the FastAPI docs-recommended pattern.

### Anti-Pattern 4: Using Celery from day one
**What:** Setting up Redis + Celery worker for email sending in Phase 1.
**Why bad:** Massive complexity increase for a feature (email) that comes in Phase 7. Adds two extra containers, complicates local development, creates failure modes before the core system is stable.
**Instead:** FastAPI `BackgroundTasks` is explicitly recommended by FastAPI docs for email notifications. Migrate to Celery only if persistence or distributed execution becomes a real requirement.

### Anti-Pattern 5: Direct ISBN API call from frontend
**What:** React calls `https://openlibrary.org/isbn/...` directly.
**Why bad:** CORS issues; the library's API key or rate limit behaviour is exposed to the client; no server-side caching or error normalisation.
**Instead:** The FastAPI backend is the sole caller of Open Library. The frontend calls `POST /catalog/books/isbn/{isbn}` and receives a normalised response.

---

## Scalability Considerations

| Concern | At 100 users (school) | At 10K users | At 1M users |
|---------|----------------------|--------------|-------------|
| DB connections | Default pool is fine | Add PgBouncer | Read replicas |
| Email throughput | BackgroundTasks (in-process) | Celery + Redis | Dedicated email service (SES) |
| Search performance | Full-text index on title/author | PostgreSQL `tsvector` GIN index | Elasticsearch |
| Fine calculation | On-return computation | Same | Precomputed / event-sourced |
| API instances | Single FastAPI container | Multiple + load balancer | Kubernetes |

For v1, the system will serve a single school. All scalability concerns beyond "100 users" are out of scope but the schema design (Copy table, fine rows, notification log) does not close off future scaling.

---

## Sources

- FastAPI JWT + RBAC: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ (HIGH confidence)
- FastAPI BackgroundTasks vs Celery: https://fastapi.tiangolo.com/tutorial/background-tasks/ (HIGH confidence)
- FastAPI larger application structure (APIRouter): https://fastapi.tiangolo.com/tutorial/bigger-applications/ (HIGH confidence)
- FastAPI CORS middleware: https://fastapi.tiangolo.com/tutorial/cors/ (HIGH confidence)
- FastAPI SQLModel ORM patterns: https://fastapi.tiangolo.com/tutorial/sql-databases/ (HIGH confidence)
- Open Library ISBN API (`/isbn/{isbn}.json`): https://openlibrary.org — MEDIUM confidence (API endpoint known from training data; direct verification blocked)
- LMS schema design (Book/Copy separation, partial unique index on loans, fine calculation pattern): established domain knowledge from standard library science systems — MEDIUM confidence, no single authoritative source
