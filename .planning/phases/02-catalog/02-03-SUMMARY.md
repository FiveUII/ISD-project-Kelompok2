---
phase: 02-catalog
plan: "03"
subsystem: frontend-catalog-ui
tags: [react, tanstack-query, tanstack-table, tailwind, shadcn, catalog, isbn-fetch, rbac]
dependency_graph:
  requires:
    - 02-01  # AppLayout shell, shadcn/ui components, authenticated route structure
    - 02-02  # Backend catalog API (GET /books, POST /books, POST /books/isbn-fetch, etc.)
  provides:
    - frontend-catalog-ui  # All four catalog pages wired and functional
  affects:
    - frontend/src/App.tsx
    - frontend/src/components/AvailabilityBadge.tsx
    - frontend/src/components/CopyStatusBadge.tsx
    - frontend/src/components/BookSearchCard.tsx
    - frontend/src/components/SearchPagination.tsx
    - frontend/src/components/ConfirmDialog.tsx
    - frontend/src/components/ISBNFetchButton.tsx
    - frontend/src/components/BookDataTable.tsx
    - frontend/src/pages/CatalogPage.tsx
    - frontend/src/pages/LibrarianBooksPage.tsx
    - frontend/src/pages/AddBookPage.tsx
    - frontend/src/pages/BookDetailPage.tsx
    - frontend/tailwind.config.js
    - frontend/src/index.css
tech_stack:
  added:
    - "@tanstack/react-table 8.x (useReactTable, getCoreRowModel, getSortedRowModel, flexRender)"
  patterns:
    - URL-driven search with useSearchParams — back/forward navigation restores results
    - TanStack Query v5 keepPreviousData for pagination (no flash between pages)
    - useMutation.isPending (not isLoading) per TanStack Query v5 API
    - Client-side sort via getSortedRowModel — no server round-trip for column sorting
    - ConfirmDialog wraps all destructive actions — zero window.confirm() usage
    - Server is source of truth for available_count — no client-side recalculation (T-03-02)
key_files:
  created:
    - frontend/src/components/AvailabilityBadge.tsx
    - frontend/src/components/CopyStatusBadge.tsx
    - frontend/src/components/BookSearchCard.tsx
    - frontend/src/components/SearchPagination.tsx
    - frontend/src/components/ConfirmDialog.tsx
    - frontend/src/components/ISBNFetchButton.tsx
    - frontend/src/components/BookDataTable.tsx
    - frontend/src/pages/CatalogPage.tsx
    - frontend/src/pages/LibrarianBooksPage.tsx
    - frontend/src/pages/AddBookPage.tsx
    - frontend/src/pages/BookDetailPage.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/tailwind.config.js
    - frontend/src/index.css
decisions:
  - "CatalogPage disables useQuery when q='' — no API call on empty search (shows prompt instead)"
  - "BookDetailPage activeCopies = book.copies.filter() retains all copies regardless of deleted_at — the API already filters deleted copies server-side"
  - "ISBNFetchButton: any non-not_found error maps to unavailable status per plan spec"
  - "Tailwind config extended with CSS variable theme tokens — required for shadcn color classes to resolve in v3"
metrics:
  duration: "18 minutes"
  completed: "2026-06-09"
  tasks_completed: 3
  tasks_total: 3
  files_created: 11
  files_modified: 3
---

# Phase 02 Plan 03: Frontend Catalog UI — Pages, Components, and DataTable Summary

**One-liner:** URL-driven catalog search page, sortable TanStack Table for librarian book management, ISBN auto-fetch form, and book detail with copies management — all wired into App.tsx with shadcn Dialog confirmations.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Shared Helper Components | b949576 | AvailabilityBadge, CopyStatusBadge, BookSearchCard, SearchPagination, ConfirmDialog, ISBNFetchButton |
| 2 | CatalogPage and BookDataTable | c7b11dd | BookDataTable.tsx, CatalogPage.tsx |
| 3 | LibrarianBooksPage, AddBookPage, BookDetailPage, App.tsx | 16557d4 | LibrarianBooksPage, AddBookPage, BookDetailPage, App.tsx |
| fix | Pre-existing Tailwind/CSS build failure | 0e78475 | tailwind.config.js, index.css |

## What Was Built

### Task 1 — Shared Helper Components

Six pure presentational components with no API calls:

- **AvailabilityBadge** — green-100/green-700 for count > 0, gray-100/gray-500 for 0. Exact Tailwind classes per spec.
- **CopyStatusBadge** — available (green), on_loan (yellow), lost (red) with consistent `inline-flex rounded-full` base classes.
- **BookSearchCard** — `Card` + `CardContent` from shadcn, cover image or BookOpen icon placeholder, title/author/ISBN/description snippet (150 char truncation), AvailabilityBadge.
- **SearchPagination** — Previous/Next with shadcn `Button variant="outline"`, current page in `text-blue-600 font-semibold` per D-05.
- **ConfirmDialog** — wraps shadcn Dialog with controlled `open`/`onOpenChange`, destructive confirm button, loading state shows "...". Zero `window.confirm()` calls.
- **ISBNFetchButton** — `idle | loading | success | not_found | unavailable` state machine, exact copywriting per UI-SPEC alert messages, shadcn Alert components.

### Task 2 — CatalogPage and BookDataTable

- **CatalogPage (`/catalog`)** — URL-driven search with `useSearchParams`; query fires on Enter or button click only (not real-time); `useQuery` with `placeholderData: keepPreviousData`; three skeleton cards during load; "Search the catalog" prompt when q=""; "No books found" when results empty; `SearchPagination` renders only when `pages > 1`.
- **BookDataTable** — TanStack Table with 5 sortable columns (Title, Author, ISBN, Available, Copies) plus non-sortable Actions. Default sort: Title asc. AvailabilityBadge in Available column. ChevronUp/Down/ChevronsUpDown icons on header buttons. Empty state row with colspan=6.

### Task 3 — Librarian Pages and App.tsx Wiring

- **LibrarianBooksPage (`/librarian/books`)** — "Manage Books" heading + "Add Book" button header row; URL-driven search using `queryKey: ["librarian-books"]`; `BookDataTable` with Edit (navigate to detail) and Delete (ConfirmDialog); `useMutation.isPending` passed to ConfirmDialog isLoading prop.
- **AddBookPage (`/librarian/books/new`)** — 6-field form (ISBN, Title, Author, Description, Publisher, Publish Year); ISBNFetchButton auto-fills title/author/description/cover_url only (publisher/year intentionally excluded per D-03); inline required-field errors; `createMutation.isPending` disables Save button; exact copywriting "Save Book" / "Discard Book".
- **BookDetailPage (`/librarian/books/:id`)** — book metadata display with inline edit form toggle ("Edit Book" / "Save Changes" / "Discard Changes"); Physical Copies section with CopyStatusBadge per copy; Add Copy inline form (barcode optional, condition select); Mark as Lost ConfirmDialog with exact copywriting; query invalidation on all mutations.
- **App.tsx** — four Wave 0 `<div>` placeholder stubs replaced with real page imports.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing Tailwind v3 / shadcn CSS variable build failure**
- **Found during:** Post-task build verification
- **Issue:** `index.css` used `@apply border-border`, `@apply bg-background text-foreground`, and `@apply font-sans` — Tailwind v3 `@apply` cannot resolve CSS variable-backed utility names unless those names are registered in `tailwind.config.js` theme. The shadcn package's `tailwind.css` uses Tailwind v4 `@theme` syntax which is incompatible with v3. This caused `npm run build` to fail with "The `border-border` class does not exist."
- **Fix:** (a) Added CSS variable color/radius/font theme extensions to `tailwind.config.js` mapping all shadcn tokens (background, foreground, card, popover, primary, secondary, muted, accent, destructive, border, input, ring). (b) Replaced all `@apply` calls in `index.css` with direct `var(--token)` CSS property assignments.
- **Files modified:** `frontend/tailwind.config.js`, `frontend/src/index.css`
- **Commit:** 0e78475
- **Scope:** Pre-existing in Wave 0/Plan 01 setup — confirmed by reverting my changes and re-running build.

## Threat Model Compliance

| Threat | Disposition | How Mitigated |
|--------|-------------|---------------|
| T-03-01 Route guard bypass | Mitigated | AppLayout handles guards — page components do not inline role checks |
| T-03-02 Client-side availability recalculation | Mitigated | available_count read directly from API response; no client math |
| T-03-03 Copywriting contract | Mitigated | All strings match exact spec: "Search the catalog", "No books found", "Fetch Details", "Save Book", "Discard Book", "Mark as Lost", "Keep Copy", "Delete", "Keep Book", Alert messages verbatim |

## Known Stubs

None. All four pages are fully wired to the backend API. No hardcoded placeholders, no TODO returns, no mock data.

## Self-Check: PASSED

Files created:
- frontend/src/components/AvailabilityBadge.tsx — FOUND
- frontend/src/components/CopyStatusBadge.tsx — FOUND
- frontend/src/components/BookSearchCard.tsx — FOUND
- frontend/src/components/SearchPagination.tsx — FOUND
- frontend/src/components/ConfirmDialog.tsx — FOUND
- frontend/src/components/ISBNFetchButton.tsx — FOUND
- frontend/src/components/BookDataTable.tsx — FOUND
- frontend/src/pages/CatalogPage.tsx — FOUND
- frontend/src/pages/LibrarianBooksPage.tsx — FOUND
- frontend/src/pages/AddBookPage.tsx — FOUND
- frontend/src/pages/BookDetailPage.tsx — FOUND

Commits:
- b949576 feat(02-03): add shared helper components — FOUND
- c7b11dd feat(02-03): add CatalogPage and BookDataTable — FOUND
- 16557d4 feat(02-03): add librarian pages and wire catalog routes — FOUND
- 0e78475 fix(02-03): resolve pre-existing Tailwind build failure — FOUND

Build verification:
- npx tsc --noEmit — PASSED (0 errors)
- npm run build — PASSED (bundle built in 4.31s)
