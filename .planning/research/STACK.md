# Technology Stack

**Project:** Library Management System
**Researched:** 2026-06-08
**Confidence:** MEDIUM-HIGH (core decisions verified via official docs; some library versions rely on training data where WebFetch was restricted)

---

## Recommended Stack

### Backend Core

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.11+ | Runtime | 3.11 is stable, fast, widely supported; 3.12+ compatible too |
| FastAPI | 0.136.x (latest) | Web framework | Official docs confirmed 0.136.3 released 2026-05-23; async-first, auto-generates OpenAPI docs, built-in dependency injection for RBAC |
| Pydantic | v2.x | Data validation | Required by FastAPI 0.100+; v2 is a complete Rust-backed rewrite, ~5-50x faster than v1 for validation |
| Uvicorn | 0.29+ | ASGI server | Official FastAPI-recommended ASGI server; use with `--workers` for production |

### Database Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL | 16 | Primary database | Project constraint; concurrent access, ACID transactions, strong JSON support for future extensibility |
| SQLAlchemy | 2.x | ORM | Use SQLAlchemy 2.0 directly over SQLModel. SQLModel is recommended in FastAPI docs but its async support is immature and has lagged behind SQLAlchemy. SQLAlchemy 2.0 has first-class async support via `AsyncSession` |
| asyncpg | 0.29+ | PostgreSQL async driver | Required for SQLAlchemy async with PostgreSQL; fastest Python-PostgreSQL driver available |
| Alembic | 1.13+ | Database migrations | The standard migration tool for SQLAlchemy; supports async migrations; do NOT manage schema changes manually |

**ORM Decision — SQLAlchemy 2.0 over SQLModel:**

SQLModel is built by the same author as FastAPI and is recommended in the official FastAPI tutorial. However:
- SQLModel's async support (needed for truly non-blocking DB operations) is documented as "in progress" and thin
- SQLAlchemy 2.0 ships mature async support (`AsyncSession`, `AsyncEngine`) verified in its own docs
- The CRUD patterns for this app (books, loans, users) are straightforward — SQLAlchemy 2.0's declarative style is clean and widely understood
- Alembic works directly with SQLAlchemy models

**Confidence:** MEDIUM — SQLModel recommendation is in official FastAPI docs, but async maturity concern is based on training-data knowledge that SQLModel async was still catching up as of early 2025. Verify current SQLModel async docs before committing.

### Authentication & Security

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PyJWT | 2.x | JWT token generation/verification | Recommended directly in FastAPI official docs (over python-jose which is unmaintained) |
| pwdlib[argon2] | latest | Password hashing | FastAPI docs explicitly recommend pwdlib + Argon2 over bcrypt; Argon2 is the current best-practice hashing algorithm |

**RBAC pattern:** Use FastAPI OAuth2 scopes via `SecurityScopes` + `Security()` dependency. Encode roles (`student`, `librarian`) as scopes in JWT payload. Validate scopes in a shared `get_current_user` dependency injected at the router level. This is the FastAPI-native pattern verified from official docs.

### External HTTP / ISBN Lookup

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| HTTPX | 0.27+ | Async HTTP client | FastAPI's own TestClient is built on HTTPX; it supports `async` natively, making it the right choice for calling Open Library API from async route handlers |
| Open Library Books API | N/A | ISBN metadata fetch | Free, no API key required, returns title/author/publisher/cover. Endpoint: `https://openlibrary.org/isbn/{isbn}.json`. Fallback: Google Books API (`https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}`) requires no key for low-volume use |

**Confidence (Open Library):** MEDIUM — API existence and no-key requirement confirmed in PROJECT.md and training data; specific rate limits were not verified due to WebFetch restrictions. Treat as requiring validation in Phase 1.

### Email / Notifications

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI `BackgroundTasks` | built-in | Trigger email sends after HTTP response | For due-date reminders triggered by librarian actions or scheduled checks; FastAPI docs confirm this pattern for "small tasks" like email |
| APScheduler | 3.10+ | Scheduled jobs | Runs periodic overdue-check jobs inside the FastAPI process. Simpler than Celery for this use case: no Redis/RabbitMQ broker needed, runs in-process |
| Resend (or SMTP via `aiosmtplib`) | latest | Email delivery | For transactional email. Resend has a generous free tier and a clean Python SDK. Alternative: `aiosmtplib` + any SMTP provider (Gmail, SendGrid) if Resend is not available in region |

**Why NOT Celery:** FastAPI docs explicitly state BackgroundTasks is appropriate for email. Celery requires a message broker (Redis or RabbitMQ) — a significant infrastructure addition for a school library system. APScheduler handles the scheduled-check use case without that overhead. Revisit if job queue requirements grow.

**Confidence:** MEDIUM — APScheduler + BackgroundTasks pattern based on training data and FastAPI docs guidance; verify APScheduler FastAPI integration pattern in Phase 3 (notifications).

### Frontend Core

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 18.x | UI framework | Project constraint; React 18 ships concurrent rendering, which improves dashboard responsiveness |
| Vite | 5.x | Build tool / dev server | Current standard for React projects in 2025; replaces Create React App (CRA is deprecated) |
| React Router | 6.x | Client-side routing | Standard routing for React; v6 has data loaders and error boundaries built in |

### Frontend State & Data Fetching

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| TanStack Query (React Query) | v5 | Server state / data fetching | The standard for server-state in React admin dashboards. Handles caching, background refetching, pagination, and mutations. Eliminates the need for Redux for server data. Version 5 is the current major version |
| Zustand | 4.x | Client-side UI state | Lightweight global state for auth (JWT token, current user role, UI flags). Much simpler than Redux for this scope |
| Axios | 1.x | HTTP client | Familiar, widely used; works well with TanStack Query as the fetcher function. Alternative: native `fetch` + custom wrapper |

**State management split:**
- Server state (books, loans, users from API) → TanStack Query
- Auth / session state (token, user role) → Zustand store (persisted to `localStorage`)
- Local UI state (modals, form state) → React `useState`

This three-layer split avoids the classic mistake of putting everything in Redux.

### Frontend UI

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Tailwind CSS | 3.x | Utility-first styling | Fast dashboard development without writing custom CSS; good for admin UIs |
| shadcn/ui | latest | Headless component library | Provides accessible, customizable components (tables, dialogs, forms) built on Radix UI + Tailwind. NOT an npm package — copies components into your repo, which avoids version lock-in |

**Why NOT Material UI (MUI) or Ant Design:** Both are heavy full-component libraries with strong visual opinions. For a school library system where you want clean, minimal UI fast, Tailwind + shadcn/ui gives more control with less bundle weight.

### Infrastructure / Deployment

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Docker | 24+ | Container runtime | Project constraint |
| Docker Compose | v2 (compose v2 CLI) | Multi-service orchestration | FastAPI docs confirm Docker Compose as the correct tool for single-server deployments with FastAPI + DB |
| Nginx | 1.25+ | Reverse proxy / static file serving | Serve the React build as static files; proxy `/api/*` to the FastAPI container. Keeps the stack self-contained — no need for a separate Node server for the frontend |

**Docker Compose service structure:**
```
services:
  db:         PostgreSQL 16 with named volume for persistence
  backend:    FastAPI (Python 3.11 + uvicorn)
  frontend:   Nginx serving React static build, proxying /api to backend
```

The React app is built at Docker build time (`npm run build`) and served as static files — no Node.js process needed in production.

### Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | 7.x | Test runner | FastAPI docs explicitly recommend pytest |
| pytest-asyncio | 0.23+ | Async test support | Required for testing async FastAPI routes and SQLAlchemy async sessions |
| httpx | 0.27+ | HTTP test client | FastAPI's `TestClient` is built on HTTPX; used directly for integration tests |
| factory-boy | 3.x | Test fixtures / factories | Clean pattern for generating test data (users, books, loans) without manual setup |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| ORM | SQLAlchemy 2.0 | SQLModel | SQLModel is higher-level and cleaner, but async support was immature; SQLAlchemy 2.0 async is battle-tested |
| ORM | SQLAlchemy 2.0 | Tortoise ORM | Tortoise has async-first design but smaller ecosystem, less Alembic integration, fewer production examples |
| Auth | PyJWT + pwdlib | python-jose | python-jose is unmaintained (FastAPI docs explicitly deprecated it in favor of PyJWT) |
| Password hash | Argon2 (pwdlib) | bcrypt | Argon2 is the current OWASP recommendation; bcrypt is still fine but older |
| Scheduler | APScheduler | Celery + Redis | Celery requires a broker (Redis/RabbitMQ) — too much infrastructure overhead for email reminders in a school library |
| Frontend UI | Tailwind + shadcn/ui | Material UI | MUI is heavier, more opinionated, slower to customize; not ideal for a data-dense admin dashboard |
| Frontend state | TanStack Query + Zustand | Redux Toolkit | Redux adds complexity for this scope; TanStack Query handles all server state, leaving only simple client state for Zustand |
| Build tool | Vite | Create React App | CRA is deprecated and unmaintained; Vite is the current standard |
| Email | BackgroundTasks + SMTP | Celery workers | Same as Celery vs APScheduler — broker overhead not justified |

---

## Installation Sketch

### Backend (`requirements.txt` or `pyproject.toml`)

```
fastapi>=0.136.0
uvicorn[standard]>=0.29.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
pydantic>=2.0.0
pyjwt>=2.8.0
pwdlib[argon2]>=0.2.0
httpx>=0.27.0
apscheduler>=3.10.0
aiosmtplib>=3.0.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
```

### Frontend (`package.json` key dependencies)

```json
{
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "react-router-dom": "^6.0.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.0.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "tailwindcss": "^3.4.0"
  }
}
```

---

## Key Patterns Summary

### FastAPI Router Organization (verified from official docs)

```
app/
  main.py              # app creation, CORS, router registration
  dependencies.py      # get_current_user, require_librarian (shared auth deps)
  routers/
    auth.py            # /auth/token
    books.py           # /books CRUD
    loans.py           # /loans checkout/return
    users.py           # /users management
  models/              # SQLAlchemy ORM models
  schemas/             # Pydantic request/response schemas
  services/            # Business logic (fine calculation, email dispatch)
  db.py                # AsyncEngine, AsyncSession, get_db dependency
```

### RBAC Pattern (verified from official docs)

Use `Security()` with OAuth2 scopes, not a custom `role` field check. Encode `["student"]` or `["librarian"]` scopes in the JWT. Dependency `require_librarian = Security(get_current_user, scopes=["librarian"])` applied at router level protects all librarian routes.

### Pagination (verified from official docs)

Standard offset/limit via query parameters: `skip: int = 0, limit: int = 20`. Enforce a maximum limit (e.g., 100) using `Annotated[int, Query(le=100)]` to prevent abuse.

### Docker Compose CORS Gotcha (verified from official docs)

When `allow_credentials=True`, `allow_origins` CANNOT be `["*"]`. Must explicitly list frontend origin (e.g., `http://localhost:5173` for Vite dev, `https://library.school.edu` for production). Use environment variable `ALLOWED_ORIGINS` to switch between dev and prod.

---

## Confidence Assessment

| Area | Confidence | Source | Notes |
|------|------------|--------|-------|
| FastAPI version (0.136.3) | HIGH | Official release notes fetched | Confirmed May 2026 |
| FastAPI auth patterns (PyJWT, pwdlib, scopes) | HIGH | Official FastAPI docs fetched | Direct quotes from docs |
| FastAPI router structure | HIGH | Official FastAPI docs fetched | Direct from bigger-applications guide |
| FastAPI pagination | HIGH | Official FastAPI docs fetched | Standard query params pattern |
| FastAPI CORS config | HIGH | Official FastAPI docs fetched | CORSMiddleware config verified |
| FastAPI BackgroundTasks for email | HIGH | Official FastAPI docs fetched | Docs say appropriate for email; Celery needed only for heavy compute |
| SQLAlchemy 2.0 over SQLModel | MEDIUM | FastAPI docs recommend SQLModel; async caveat from training data | Verify SQLModel async status before starting DB layer |
| asyncpg as PostgreSQL driver | MEDIUM | Training data + ecosystem knowledge | Standard pairing; verify version compatibility |
| Alembic for migrations | MEDIUM | Training data; widely used standard | Low risk; standard tool |
| TanStack Query v5 | MEDIUM | Training data; version may need verification | Verify v5 API at tanstack.com before using |
| Zustand v4 | MEDIUM | Training data | Widely used; verify current version |
| Vite v5 | MEDIUM | Training data | CRA deprecation is well-established fact |
| shadcn/ui | MEDIUM | Training data | Rapidly evolving; verify setup approach |
| APScheduler for scheduled jobs | MEDIUM | Training data; FastAPI docs confirm BackgroundTasks pattern | Verify APScheduler + FastAPI integration example |
| Open Library API | MEDIUM | Referenced in PROJECT.md; training data | Confirm rate limits and ISBN endpoint response shape in Phase 1 |
| Docker Compose structure | HIGH | Official FastAPI deployment docs fetched | Single-server Compose pattern confirmed |

---

## Sources

- FastAPI release notes: https://fastapi.tiangolo.com/release-notes/ (fetched 2026-06-08, confirms 0.136.3)
- FastAPI JWT/OAuth2 auth: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ (fetched)
- FastAPI OAuth2 scopes / RBAC: https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/ (fetched)
- FastAPI bigger applications / router structure: https://fastapi.tiangolo.com/tutorial/bigger-applications/ (fetched)
- FastAPI pagination: https://fastapi.tiangolo.com/tutorial/query-params/ (fetched)
- FastAPI CORS: https://fastapi.tiangolo.com/tutorial/cors/ (fetched)
- FastAPI background tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/ (fetched)
- FastAPI Docker deployment: https://fastapi.tiangolo.com/deployment/docker/ (fetched)
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/ (fetched)
- FastAPI SQL databases (SQLModel recommendation): https://fastapi.tiangolo.com/tutorial/sql-databases/ (fetched)
- React Context for auth state: https://react.dev/reference/react/useContext (fetched)
