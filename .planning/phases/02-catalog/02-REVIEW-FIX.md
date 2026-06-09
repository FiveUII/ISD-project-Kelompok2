---
phase: 02-catalog
fixed_at: 2026-06-09T06:08:34Z
review_path: .planning/phases/02-catalog/02-REVIEW.md
iteration: 1
findings_in_scope: 10
fixed: 10
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-06-09T06:08:34Z
**Source review:** .planning/phases/02-catalog/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 10 (4 Critical + 6 Warning)
- Fixed: 10
- Skipped: 0

---

## Fixed Issues

### CR-01: `CopyCondition` enum missing `"new"` — 422 on Add Copy

**Files modified:** `backend/app/core/enums.py`, `backend/alembic/versions/0004_add_new_copycondition.py`
**Commit:** `6196208`
**Applied fix:** Added `new = "new"` as the first variant to `CopyCondition` enum. Created migration `0004_add_new_copycondition.py` that runs `ALTER TYPE copycondition ADD VALUE IF NOT EXISTS 'new'` to update the PostgreSQL enum type.

---

### CR-02: SSRF path-injection via unvalidated Open Library key

**Files modified:** `backend/app/services/isbn_service.py`
**Commit:** `3ca6096`
**Applied fix:** Added `AUTHOR_KEY_RE = re.compile(r"^/authors/OL\d+A$")` and `WORK_KEY_RE = re.compile(r"^/works/OL\d+W$")` module-level regex constants. Guarded both Step 2 (author fetch) and Step 3 (works fetch) with `AUTHOR_KEY_RE.match(author_key)` and `WORK_KEY_RE.match(work_key)` respectively — keys that do not match the expected Open Library path format are silently skipped, preventing SSRF redirection to arbitrary hosts.

---

### CR-03: `CopyStatusBadge` crashes on `"withdrawn"` status

**Files modified:** `frontend/src/components/CopyStatusBadge.tsx`, `frontend/src/pages/BookDetailPage.tsx`
**Commit:** `6d1a294`
**Applied fix:** Added `"withdrawn"` to the `CopyStatus` type union and added `withdrawn: { label: "Withdrawn", colorClass: "bg-gray-100 text-gray-500" }` to `STATUS_MAP`. Changed the destructure from `const { label, colorClass } = STATUS_MAP[status]` to a null-coalescing pattern `const entry = STATUS_MAP[status] ?? { ... }` as a belt-and-suspenders fallback. Also updated the `Copy` interface's `status` type in `BookDetailPage.tsx` to include `"withdrawn"`.

---

### CR-04: Migration creates B-tree indexes useless for `ILIKE '%q%'` search

**Files modified:** `backend/alembic/versions/0003_catalog_indexes.py`
**Commit:** `d1e43ef`
**Applied fix:** Rewrote migration 0003 entirely. Replaced `op.create_index(...)` B-tree calls with `op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")` followed by two `CREATE INDEX ... USING gin (... gin_trgm_ops)` statements for `ix_books_title_trgm` and `ix_books_author_trgm`. Updated the downgrade to use `DROP INDEX IF EXISTS`. Updated the module docstring to correctly describe the indexes and explain why B-tree cannot accelerate substring ILIKE patterns.

---

### WR-01: All three mutation `onError` handlers are absent — failures are silent

**Files modified:** `frontend/src/pages/LibrarianBooksPage.tsx`, `frontend/src/pages/BookDetailPage.tsx`
**Commit:** `074bc57`
**Applied fix:** Added `onError` callback to all four mutations: `deleteMutation` (LibrarianBooksPage), `updateMutation`, `addCopyMutation`, and `markLostMutation` (BookDetailPage). Each `onError` sets a state variable with a user-visible error message. Added a corresponding error message element to the JSX in both pages. Added `setErrorMessage("")` / `setMutationError("")` calls in `onSuccess` so stale errors clear on the next successful operation.

---

### WR-02: Edit form silently clears title/author if whitespace-only values are submitted

**Files modified:** `frontend/src/pages/BookDetailPage.tsx`, `backend/app/schemas/catalog.py`
**Commits:** `70adf3f` (frontend validation), `6eedfca` (schema constraint)
**Applied fix:** Added client-side required validation to `handleSaveChanges` — returns early with a visible error message if `editTitle.trim()` or `editAuthor.trim()` is empty. Changed the payload to use `editTitle.trim()` and `editAuthor.trim()` unconditionally (not `|| undefined`) since the validation gate prevents blank values from reaching the mutation. Added `Field(None, min_length=1)` to `BookUpdate.title` and `BookUpdate.author` in the Pydantic schema as a server-side safety net.

---

### WR-03: `publish_year` parsed with `parseInt` — `NaN` is silently submitted

**Files modified:** `frontend/src/pages/AddBookPage.tsx`, `frontend/src/pages/BookDetailPage.tsx`
**Commit:** `5138dbd`
**Applied fix:** Replaced the single-line `parseInt` calls with a two-step pattern: parse to `yearInt`, then guard with `!isNaN(yearInt)` before including in the payload. In `AddBookPage`, extracted to `const yearInt = parseInt(publishYear, 10)` with an `if (publishYear.trim() && !isNaN(yearInt))` block. In `BookDetailPage`, used an IIFE inline for the payload field to keep it within the existing object literal structure.

---

### WR-04: `activeCopies` filter retains all copies including lost ones

**Files modified:** `frontend/src/pages/BookDetailPage.tsx`
**Commit:** `dd4ac21`
**Applied fix:** Replaced the always-true `book.copies.filter((c) => c.status !== undefined)` with a direct assignment `const allCopies = book.copies` with an explanatory comment. Updated all downstream references from `activeCopies` to `allCopies`. The librarian's view intentionally shows all copies (including lost) for audit purposes, which is now explicit rather than accidentally implied.

---

### WR-05: `CatalogPage` / `LibrarianBooksPage` missing `isError` state

**Files modified:** `frontend/src/pages/CatalogPage.tsx`, `frontend/src/pages/LibrarianBooksPage.tsx`
**Commit:** `8c3f38c`
**Applied fix:** Added `isError` to the `useQuery` destructure in both pages. In `CatalogPage`, added an `isError` branch that renders a "Search failed" error block, and added `!isError` guards to the "No books found" and results blocks to prevent showing stale data on error. In `LibrarianBooksPage`, added an `isError` block that renders a "Failed to load books" message above the table.

---

### WR-06: `debug print` statement in production `require_admin` dependency

**Files modified:** `backend/app/dependencies.py`
**Commit:** `c4a0ead`
**Applied fix:** Removed the `print(f"[require_admin] ...")` statement entirely. The statement logged user email addresses and admin config to stdout on every admin endpoint call, causing information disclosure in container logs.

---

_Fixed: 2026-06-09T06:08:34Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
