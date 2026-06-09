# Phase 2: Catalog - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 delivers the complete book catalog feature set: librarians can add books (manually or via ISBN auto-fetch from Open Library), edit book details, soft-delete books, manage physical copies (add copies, mark as lost), and search the catalog. Students can search the catalog by title, author, or ISBN using a single search box and see an accurate count of currently available copies.

This phase does NOT deliver loans, returns, fines, overdue tracking, or email notifications — those are Phases 3–4.

</domain>

<decisions>
## Implementation Decisions

### ISBN Auto-Fetch (Open Library API)
- **D-01:** When Open Library returns no result for an ISBN: show an inline error message ("No book found for this ISBN"), keep the librarian on the form, and let them fill in all fields manually.
- **D-02:** When Open Library is unreachable (network timeout / 5xx): show an inline error message ("Service unavailable — please fill in details manually"). No retry logic. Consistent with D-01 error pattern.
- **D-03:** When Open Library returns data, auto-fill exactly three fields: title, author, description. These are the three fields scoped in CATL-02. Publisher and publish_year are NOT auto-filled (even if Open Library returns them) to keep the behavior predictable and minimal.

### Search
- **D-04:** Catalog search uses PostgreSQL ILIKE substring matching. No trigram/fuzzy search — the pg_trgm extension is not needed. One search query checks all three fields (title OR author OR ISBN). This is a single API call with one `q` query parameter.
- **D-05:** Search results use offset-based pagination: 20 results per page, page 1/2/3 navigation controls. FastAPI query params: `?q=&page=1&page_size=20`.
- **D-06:** Soft-deleted books are excluded from ALL search results, for both students and librarians. The `deleted_at IS NULL` filter is applied universally. No "show deleted" view in Phase 2.

### Catalog UI Layout & Routing
- **D-07:** Student search and librarian catalog management live on SEPARATE routes:
  - `/catalog` — public student search page (accessible to authenticated students)
  - `/librarian/books` — librarian book list (protected, `require_librarian` DI)
  - `/librarian/books/new` — add new book form
  - `/librarian/books/:id` — book detail + copy management (librarian)
- **D-08:** Physical copies are managed INLINE on the book detail page (`/librarian/books/:id`). A "Copies" section below the book details lists all non-deleted copies with status, and provides "Add Copy" and "Mark as Lost" actions. No separate `/copies` route.
- **D-09:** The librarian book list uses a shadcn/ui DataTable with sortable columns: title, author, ISBN, available copies count, total copies. Row-level actions: Edit, Delete (soft-delete).
- **D-10:** Phase 2 introduces a shared navigation layout shell. Auth pages (login, register, etc.) remain outside the shell. Authenticated pages (catalog + librarian views) are wrapped in the shell layout with a top navbar. Nav links: student sees "Catalog"; librarian sees "Catalog" + "Manage Books". This layout component is the pattern for Phases 3 & 4 to add their nav items.

### Availability Display
- **D-11:** Students see only the available copy count in search results (e.g., "3 available"). NOT "3 of 5" — total copies are internal library management data, not student-facing.
- **D-12:** Available copy count is included directly in the book list API response (computed via a SQL subquery or correlated count). No separate per-book availability endpoint. This prevents N+1 queries.

### Claude's Discretion
- **Open Library API timeout:** Set a reasonable timeout (e.g., 5 seconds) on the HTTPX call. If it hits the timeout, treat as unreachable (D-02 path).
- **Student catalog access:** The `/catalog` route requires authentication (students must be logged in). It is NOT a public unauthenticated page. Unauthenticated users are redirected to `/login`.
- **Librarian student search:** Librarians can also use `/catalog` to search — they have full access. `/librarian/books` is the management view.
- **Copy status shown to librarians:** In the book detail copies section, show each copy's full status (available / on loan / lost) and barcode (if set). Copies soft-deleted (lost + deleted_at set) are hidden.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Core value, tech stack constraints, out-of-scope boundaries
- `.planning/REQUIREMENTS.md` — CATL-01 through CATL-06 (librarian management) and CATS-01, CATS-02 (student search) are the Phase 2 requirements

### Roadmap
- `.planning/ROADMAP.md` §Phase 2 — Success criteria (4 items), requirement list, UI hint flag

### Phase 1 Context (required reading — patterns established here)
- `.planning/phases/01-foundation-auth/01-CONTEXT.md` — Auth model, Docker setup, RBAC DI pattern, JWT decisions all carry forward

### Research Findings
- `.planning/research/STACK.md` — Technology choices with versions: FastAPI, SQLAlchemy 2.0 async, HTTPX for Open Library calls, React 18 + Vite 5, TanStack Query v5, shadcn/ui DataTable
- `.planning/research/ARCHITECTURE.md` — Book/Copy schema decisions (Book has no availability columns — computed from Copy rows), soft-delete pattern, RBAC via DI
- `.planning/research/PITFALLS.md` — Pitfall C1 (never add availability columns to Book), Pitfall C4 (RBAC at router level, not inline)

### Existing Code
- `backend/app/models/book.py` — Book model (id, isbn, title, author, publisher, publish_year, description, cover_url, deleted_at, copies relationship)
- `backend/app/models/copy.py` — Copy model (id, book_id, barcode, condition, status enum, deleted_at)
- `backend/app/dependencies.py` — `require_librarian` and `get_current_user` DI functions — USE THESE for protected catalog routes
- `backend/app/routers/auth.py` — Router pattern to follow: `APIRouter(prefix=..., tags=[...])`, registered in `main.py`
- `frontend/src/App.tsx` — React Router setup to extend with catalog routes
- `backend/app/schemas/auth.py` — Pydantic schema pattern to follow for catalog schemas

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/dependencies.py` — `require_librarian`, `get_current_user`, `require_admin` DI functions. Use `require_librarian` at the APIRouter level for all `/librarian/*` routes.
- `backend/app/core/db.py` — `get_db` dependency (AsyncSession) — follow existing pattern in new catalog routers.
- `backend/app/core/enums.py` — `CopyStatus`, `CopyCondition` enums already defined.
- `frontend/src/store/` — Zustand auth store (token, user role). Use `user.role` to render role-specific nav links in the layout shell.
- `frontend/src/lib/` — Axios instance and utility helpers.

### Established Patterns
- **Router-level RBAC:** `router = APIRouter(prefix="/librarian", dependencies=[Depends(require_librarian)])` — apply this pattern to all librarian catalog endpoints (PITFALLS C4).
- **SQLAlchemy async:** All DB operations use `AsyncSession` + `await session.execute(select(...))` pattern.
- **Pydantic v2 schemas:** Input schemas (request bodies) and output schemas (response models) are in `backend/app/schemas/`. New catalog schemas go in `backend/app/schemas/catalog.py`.
- **TanStack Query v5:** Server state (book list, search results) fetched via `useQuery` / `useMutation`. Auth state (token, role) from Zustand store.
- **shadcn/ui:** Components installed into `frontend/src/components/ui/`. The DataTable pattern from shadcn/ui docs applies directly to the librarian book list.

### Integration Points
- `backend/app/main.py` — Register new catalog routers here (follow `auth.router` include pattern).
- `frontend/src/App.tsx` — Add catalog routes inside the shared layout shell component.
- `backend/app/models/__init__.py` — Ensure new models/relationships are imported for Alembic autogenerate (if any schema changes needed — Phase 2 likely adds no new tables but may add indexes).

</code_context>

<specifics>
## Specific Ideas

- Layout shell with top navbar, role-aware links: students see "Catalog", librarians see "Catalog" + "Manage Books"
- shadcn/ui DataTable for librarian book list — sortable columns, row actions
- ISBN auto-fetch as a dedicated button on the Add Book form (not auto-triggered on blur) — librarian clicks "Fetch Details" after entering the ISBN
- Available copies shown as a badge or count chip in both search results and librarian book list

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-Catalog*
*Context gathered: 2026-06-09*
