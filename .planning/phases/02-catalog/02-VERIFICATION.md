---
phase: 02-catalog
verified: 2026-06-09T00:00:00Z
status: human_needed
score: 13/13 must-haves verified
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Student visits /catalog, enters a search query, presses Enter, and sees paginated cards with AvailabilityBadge"
    expected: "URL changes to /catalog?q=<term>&page=1, BookSearchCard components render with green/gray availability badge, back/forward navigation restores results"
    why_human: "Requires a running browser with a live backend — grep cannot verify rendered card output or URL state transitions"
  - test: "Librarian visits /librarian/books — non-librarian student token is redirected"
    expected: "Student navigating to /librarian/books is redirected to /catalog, not /login"
    why_human: "Route guard behavior requires a running app with two distinct JWT sessions"
  - test: "ISBN fetch on /librarian/books/new: enter a valid ISBN, click Fetch Details, observe alert and field population"
    expected: "Title, author, description auto-fill; green Alert reads exactly 'Details filled from Open Library. Review and save.' Publisher and Publish Year remain blank (D-03)"
    why_human: "Requires live Open Library API call with a real ISBN; network behavior cannot be verified statically"
  - test: "ISBN not-found alert text matches spec exactly"
    expected: "Alert reads exactly 'No book found for this ISBN. Fill in the details manually.'"
    why_human: "Alert variant rendering (default vs. warning color) and exact string must be checked in browser"
  - test: "Delete confirmation: click Delete in DataTable — shadcn Dialog opens; no browser confirm() dialog fires"
    expected: "ConfirmDialog opens with title 'Delete book', description 'This will remove the book from the catalog. Loan history is preserved. This action cannot be undone.', buttons 'Delete' and 'Keep Book'"
    why_human: "Dialog rendering and button label exactness require browser-level visual check"
  - test: "Mark as Lost flow in BookDetailPage — confirm dialog opens, copy status updates after confirmation"
    expected: "Dialog opens with title 'Mark copy as lost', confirm 'Mark as Lost', cancel 'Keep Copy'; after confirm the copy row shows 'Lost' badge and Mark as Lost button disappears"
    why_human: "Requires live API mutation + React Query re-render cycle; cannot be statically verified"
  - test: "Book availability count is accurate after adding/losing a copy"
    expected: "available_count in catalog and librarian views updates immediately after copy status changes (no stale data from React Query cache)"
    why_human: "Success Criterion 4 (immediate availability update) requires exercising the full mutation + invalidation + re-fetch cycle in a live environment"
---

# Phase 2: Catalog — Verification Report

**Phase Goal:** Deliver the complete book catalog — students can search/browse books with availability counts; librarians can add (manual + ISBN auto-fetch), edit, soft-delete books, manage physical copies, and mark copies as lost. All routes are role-gated at the AppLayout level.
**Verified:** 2026-06-09
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | shadcn/ui initialized with path alias resolving in Vite and TypeScript | VERIFIED | `vite.config.ts` has `resolve.alias: { "@": path.resolve(__dirname, "./src") }`; `tsconfig.json` has `baseUrl: "."` and `paths: { "@/*": ["./src/*"] }`; `components.json` exists with `style: "base-nova"` |
| 2 | AppLayout wraps authenticated routes — students see Catalog nav link, librarians see Catalog + Manage Books | VERIFIED | `AppLayout.tsx` renders `<NavBar />` + `<Outlet />`; `NavBar.tsx` conditionally renders Manage Books link only when `user?.role === "librarian"` |
| 3 | App.tsx routes /catalog and /librarian/* nested under AppLayout with role guards | VERIFIED | `App.tsx` shows `<Route element={<AppLayout />}>` wrapping `/catalog` and `<Route element={<AppLayout requireLibrarian />}>` wrapping all three librarian routes; no placeholder stubs remain |
| 4 | Alembic migration 0003 chains from 0002 and creates ix_books_title + ix_books_author indexes | VERIFIED | `0003_catalog_indexes.py` has `revision = "0003"`, `down_revision = "0002"`, `upgrade()` calls `op.create_index("ix_books_title", ...)` and `op.create_index("ix_books_author", ...)`; `downgrade()` drops both |
| 5 | GET /api/books returns paginated list with available_count per book via correlated subquery (no N+1) | VERIFIED | `books.py` defines `available_count_subq` and `total_count_subq` as `.correlate(Book).scalar_subquery()`; `list_books` uses `select(Book, available_count_subq, total_count_subq)` — single query, no loop |
| 6 | POST /api/books creates a book; PUT updates it; DELETE sets deleted_at (soft-delete) | VERIFIED | `create_book`, `update_book`, and `delete_book` endpoints all present in `books.py`; `delete_book` sets `book.deleted_at = datetime.now(tz=timezone.utc)` |
| 7 | POST /api/books/isbn-fetch calls Open Library 3-step chain with correct error handling | VERIFIED | `isbn_service.py` performs edition → author → works chain; returns `ISBNFetchResponse(found=False, error="not_found")` on 404 and `ISBNFetchResponse(found=False, error="unavailable")` on any exception |
| 8 | ISBN fetch handles polymorphic description via `_extract_description()` | VERIFIED | `_extract_description()` handles `None`, plain `str`, and `dict` with `"value"` key |
| 9 | POST /api/books/{id}/copies adds a physical copy; PATCH /api/copies/{id}/lost marks copy lost and sets deleted_at | VERIFIED | `add_copy` endpoint present; `mark_copy_lost` in `copies_router` sets both `copy.status = CopyStatus.lost` and `copy.deleted_at` |
| 10 | All librarian routes reject non-librarian users with 403 via router-level Depends(require_librarian) | VERIFIED | `librarian_router` and `copies_router` both have `dependencies=[Depends(require_librarian)]` at the router level; no inline per-route checks |
| 11 | deleted_at IS NULL filter applied on all book and copy queries | VERIFIED | Every `select(Book...)` in `books.py` includes `Book.deleted_at.is_(None)`; every Copy query includes `Copy.deleted_at.is_(None)` |
| 12 | ISBN input validated server-side: alphanumeric + hyphens only (SSRF prevention) | VERIFIED | `_validate_isbn()` uses regex `r"^[a-zA-Z0-9-]{8,17}$"` applied before any HTTPX call; `HTTPException(400)` raised on failure |
| 13 | Student catalog search page, librarian management page, add book form, and book detail page are built and wired to App.tsx with real page imports | VERIFIED | `App.tsx` imports `CatalogPage`, `LibrarianBooksPage`, `AddBookPage`, `BookDetailPage`; all four files exist and contain substantive implementations with useQuery/useMutation calls to live API endpoints |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/AppLayout.tsx` | Auth shell with NavBar + Outlet | VERIFIED | Auth guard (`!token → /login`), role guard (`requireLibrarian && role !== "librarian" → /catalog`), renders NavBar + Outlet |
| `frontend/src/components/NavBar.tsx` | Role-aware navbar with logout | VERIFIED | Logo link, Catalog link for all, Manage Books link for librarians only, logout clears auth store + navigates to /login |
| `frontend/src/App.tsx` | Routes with AppLayout wrapper | VERIFIED | Real page imports (no placeholder divs); correct route nesting |
| `backend/alembic/versions/0003_catalog_indexes.py` | Index migration chained from 0002 | VERIFIED | revision=0003, down_revision=0002, correct upgrade/downgrade |
| `backend/app/schemas/catalog.py` | Pydantic v2 catalog schemas | VERIFIED | All 7 schemas present: BookCreate, BookUpdate, CopyCreate, CopyResponse, BookResponse, BookDetailResponse, BookListResponse, ISBNFetchResponse |
| `backend/app/services/isbn_service.py` | Open Library 3-step fetch service | VERIFIED | `_validate_isbn`, `_extract_description`, `_build_cover_url`, `fetch_book_by_isbn` all present and substantive |
| `backend/app/routers/books.py` | All catalog API endpoints | VERIFIED | student_router (GET /books, GET /books/{id}), librarian_router (isbn-fetch, POST/PUT/DELETE /books, POST copies), copies_router (PATCH /copies/{id}/lost) |
| `backend/app/main.py` | Books router registered under /api | VERIFIED | `app.include_router(books.student_router, prefix="/api")`, `app.include_router(books.librarian_router, prefix="/api")`, `app.include_router(books.copies_router, prefix="/api")` |
| `frontend/src/pages/CatalogPage.tsx` | Student search at /catalog | VERIFIED | URL-driven search with useSearchParams, useQuery with keepPreviousData, enabled only when q !== "", 3 skeleton cards on load, prompt/empty states, BookSearchCard rendering |
| `frontend/src/pages/LibrarianBooksPage.tsx` | Librarian management at /librarian/books | VERIFIED | "Manage Books" heading, Add Book button, URL-driven search, BookDataTable, ConfirmDialog for delete, useMutation with isPending |
| `frontend/src/pages/AddBookPage.tsx` | Add book form at /librarian/books/new | VERIFIED | 6 fields, ISBNFetchButton wired with handleFetchResult, validation on title/author, createMutation on submit, redirect on success, "Save Book"/"Discard Book" buttons |
| `frontend/src/pages/BookDetailPage.tsx` | Book detail + copies at /librarian/books/:id | VERIFIED | Book metadata display, inline edit form, Physical Copies section, Add Copy form, Mark as Lost ConfirmDialog with correct copywriting |
| `frontend/src/components/BookDataTable.tsx` | Sortable DataTable with row actions | VERIFIED | TanStack Table with 5 sortable columns + Actions, default sort Title asc, AvailabilityBadge in Available column, empty state row |
| `frontend/src/components/AvailabilityBadge.tsx` | Green/gray availability count chip | VERIFIED | count > 0: bg-green-100/text-green-700; count === 0: bg-gray-100/text-gray-500 |
| `frontend/src/components/ConfirmDialog.tsx` | Reusable Dialog for destructive confirmations | VERIFIED | shadcn Dialog, controlled open/onOpenChange, variant="destructive" confirm, loading state shows "...", no window.confirm() |
| `frontend/src/components/ui/` | All 10 shadcn components | VERIFIED | button, input, label, table, badge, dialog, card, separator, skeleton, alert — all present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/src/App.tsx` | `AppLayout` | Route element wrapping catalog + librarian/* routes | WIRED | Import present; `<Route element={<AppLayout />}>` and `<Route element={<AppLayout requireLibrarian />}>` both in use |
| `NavBar` | `useAuthStore` | `user.role` conditional rendering of nav links | WIRED | `const { user, logout } = useAuthStore()` at line 10; `user?.role === "librarian"` gate on Manage Books link |
| `backend/app/routers/books.py` | `backend/app/services/isbn_service.py` | `POST /api/books/isbn-fetch` calls `fetch_book_by_isbn()` | WIRED | `from app.services.isbn_service import fetch_book_by_isbn`; `return await fetch_book_by_isbn(isbn)` in isbn_fetch endpoint |
| `backend/app/routers/books.py` | `backend/app/dependencies.py` | `require_librarian` on librarian router, `get_current_user` on student router | WIRED | `from app.dependencies import get_current_user, require_librarian`; both used in router-level `dependencies=[Depends(...)]` |
| `backend/app/main.py` | `backend/app/routers/books.py` | `app.include_router(books.student_router, prefix="/api")` | WIRED | All three routers (student, librarian, copies) included in main.py under `/api` prefix |
| `frontend/src/pages/CatalogPage.tsx` | `/api/books` | `useQuery` with queryKey `["books", {q, page, page_size}]` and `placeholderData: keepPreviousData` | WIRED | `apiClient.get("/books", { params: ... })` inside queryFn; query disabled when `q === ""` |
| `frontend/src/pages/AddBookPage.tsx` | `/api/books/isbn-fetch` | `ISBNFetchButton` calls `POST /api/books/isbn-fetch` and populates form fields | WIRED | `ISBNFetchButton` imported and used with `isbn={isbn}` prop and `onResult={handleFetchResult}`; `handleFetchResult` calls setTitle/setAuthor/setDescription/setCoverUrl |
| `frontend/src/App.tsx` | Real page components | Replace placeholder div stubs with actual imports | WIRED | All four pages imported by name; no `<div>Coming soon</div>` stubs present |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `CatalogPage.tsx` | `data.items` | `useQuery → apiClient.get("/books")` → `GET /api/books` → SQLAlchemy query with correlated subqueries | Yes — DB query in `list_books` endpoint | FLOWING |
| `LibrarianBooksPage.tsx` | `data.items` | `useQuery → apiClient.get("/books")` (same endpoint, different queryKey) | Yes — same DB-backed endpoint | FLOWING |
| `BookDataTable.tsx` | `books` prop | Passed from LibrarianBooksPage `data?.items ?? []` | Yes — data flows from API response | FLOWING |
| `BookDetailPage.tsx` | `book` | `useQuery → apiClient.get("/books/${id}")` → `GET /api/books/{book_id}` | Yes — DB query with copies subquery | FLOWING |
| `AddBookPage.tsx` | form field state | ISBNFetchButton `onResult` populates title/author/description/cover_url; manual input otherwise | Yes — live API or user input | FLOWING |

### Behavioral Spot-Checks

Step 7b skipped — no runnable backend entry point available in this environment (project is Docker-only; asyncpg not installed locally per SUMMARY deviation note). Logic verified statically via code inspection.

### Probe Execution

Step 7c: No probe scripts found in `scripts/*/tests/probe-*.sh` pattern. No probes declared in PLAN frontmatter. Phase uses Docker-only execution model; no standalone probe scripts were written for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| CATL-01 | 02-02, 02-03 | Librarian can add a book manually | SATISFIED | `POST /api/books` in `books.py`; AddBookPage form with title/author/ISBN/description fields; Save Book button calls createMutation |
| CATL-02 | 02-02, 02-03 | Librarian can auto-fetch book details by ISBN (Open Library) | SATISFIED | `fetch_book_by_isbn()` in `isbn_service.py` implements 3-step OL fetch; ISBNFetchButton in AddBookPage calls `POST /api/books/isbn-fetch` and auto-populates title/author/description/cover_url |
| CATL-03 | 02-02, 02-03 | Librarian can edit any book's details | SATISFIED | `PUT /api/books/{id}` with `model_dump(exclude_unset=True)`; BookDetailPage inline edit form with "Save Changes"/"Discard Changes" buttons |
| CATL-04 | 02-02, 02-03 | Librarian can soft-delete a book (preserves loan history) | SATISFIED | `DELETE /api/books/{id}` sets `book.deleted_at`; ConfirmDialog in LibrarianBooksPage with "Delete"/"Keep Book" labels; no browser confirm() |
| CATL-05 | 02-02, 02-03 | Librarian can add physical copies of a book | SATISFIED | `POST /api/books/{id}/copies` endpoint; Add Copy form in BookDetailPage with barcode + condition fields |
| CATL-06 | 02-02, 02-03 | Librarian can update copy status (mark as lost) | SATISFIED | `PATCH /api/copies/{id}/lost` in `copies_router` sets `status=lost` AND `deleted_at`; Mark as Lost ConfirmDialog in BookDetailPage |
| CATS-01 | 02-02, 02-03 | Student can search catalog by title, author, or ISBN | SATISFIED | `GET /api/books?q=...` with ILIKE on all three fields; CatalogPage with URL-driven search; Enter key and Search Catalog button trigger search |
| CATS-02 | 02-02, 02-03 | Student can see available copy count per book | SATISFIED | `available_count` returned via correlated subquery on every `GET /api/books` row; AvailabilityBadge renders count in BookSearchCard |

All 8 requirements declared in PLAN frontmatter are satisfied. No orphaned requirements found — REQUIREMENTS.md traceability table maps exactly CATL-01 through CATL-06 and CATS-01/CATS-02 to Phase 2 and all 8 are covered.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TBD, FIXME, or XXX markers found in any Phase 2 modified file. No placeholder returns, empty implementations, or hardcoded empty arrays passed to rendering components. No `window.confirm()` calls. All Wave 0 `<div>Coming soon</div>` stubs confirmed removed from App.tsx and replaced with real page imports.

### Human Verification Required

#### 1. Student Catalog Search Flow

**Test:** Open /catalog in a browser, enter a query in the search input, press Enter or click "Search Catalog".
**Expected:** URL updates to `/catalog?q=<term>&page=1`; BookSearchCard components render with title, author, description snippet (max 150 chars), and AvailabilityBadge; back-navigation restores results.
**Why human:** URL state transitions, rendered card layout, and browser history behavior require a running application.

#### 2. Student Route Guard

**Test:** Log in as a student (role=student) and navigate directly to `/librarian/books`.
**Expected:** Immediately redirected to `/catalog`, not to `/login`.
**Why human:** Requires two distinct JWT sessions in a live browser; AppLayout role guard logic is correct in code but runtime behavior must be confirmed.

#### 3. ISBN Fetch — Success Path

**Test:** Navigate to `/librarian/books/new`, enter a valid ISBN (e.g. `9780140449136`), click "Fetch Details".
**Expected:** Title, author, description auto-fill; Publisher and Publish Year remain blank; green Alert reads exactly "Details filled from Open Library. Review and save."
**Why human:** Live Open Library API call; string exactness and field population require browser + network.

#### 4. ISBN Fetch — Not-Found Path

**Test:** Enter an invalid/unknown ISBN (e.g. `0000000000000`), click "Fetch Details".
**Expected:** Alert renders with text "No book found for this ISBN. Fill in the details manually."
**Why human:** Exact copywriting and alert variant rendering must be checked in browser.

#### 5. Delete Confirmation Dialog

**Test:** In `/librarian/books`, click the Delete action for any book.
**Expected:** shadcn Dialog (not browser `confirm()`) opens with title "Delete book", correct description, "Delete" and "Keep Book" buttons. Clicking "Keep Book" closes the dialog with no change; clicking "Delete" removes the book and shows invalidated query.
**Why human:** Dialog rendering, absence of browser confirm(), and mutation result all require a running app.

#### 6. Mark as Lost — Copy Status Update

**Test:** In `/librarian/books/:id`, click "Mark as Lost" on an available copy.
**Expected:** ConfirmDialog opens with title "Mark copy as lost", description matching the copy label, "Mark as Lost"/"Keep Copy" buttons. After confirming: copy row shows "Lost" (red) badge; "Mark as Lost" button disappears from that row.
**Why human:** React Query invalidation + re-render cycle with live API mutation must be exercised in browser.

#### 7. Book Availability Accuracy After Status Change (SC-4)

**Test:** Add a copy to a book (it increments available count); then mark it as lost.
**Expected:** available_count on `/catalog` search results and `/librarian/books` DataTable reflects the change immediately after the action (no stale data).
**Why human:** Success Criterion 4 specifies "updates immediately" — verifying React Query cache invalidation and absence of stale data requires a live environment.

---

## Summary

All 13 must-have truths are VERIFIED at all four levels (exists, substantive, wired, data-flowing). The full artifact set is present: all 10 shadcn/ui components, all 9 custom components, all 4 catalog pages, the backend catalog API with 3 routers, the Pydantic schemas, the ISBN fetch service, and the Alembic 0003 migration.

Key correctness checks confirmed:
- Correlated subqueries for availability counts (no N+1)
- Router-level RBAC via `Depends(require_librarian)` — never inline
- `deleted_at.is_(None)` filter on every Book and Copy query
- SSRF prevention via `_validate_isbn()` regex before any HTTPX call
- `_extract_description()` handles all three polymorphic OL response shapes
- TanStack Query v5 syntax: `isPending` on mutations, `keepPreviousData` on paginated queries
- No `window.confirm()` usage — all destructive actions use shadcn Dialog
- Wave 0 placeholder stubs removed from App.tsx

7 human verification items identified covering the 4 ROADMAP success criteria that require live browser + API exercise. All are observable behavior checks that cannot be verified by static code analysis.

---

_Verified: 2026-06-09_
_Verifier: Claude (gsd-verifier)_
