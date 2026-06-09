---
phase: 02-catalog
plan: 01
subsystem: frontend-shell, backend-migrations
tags: [shadcn, path-alias, nav-shell, alembic, route-guards]
dependency_graph:
  requires: []
  provides:
    - "@/* path alias in Vite and TypeScript"
    - "shadcn/ui initialized with 10 components at frontend/src/components/ui/"
    - "AppLayout authenticated shell with NavBar"
    - "Catalog and librarian routes wired in App.tsx with role guards"
    - "Alembic migration 0003 (ix_books_title, ix_books_author)"
  affects:
    - "02-02 (backend catalog API — unblocked)"
    - "02-03 (frontend catalog pages — unblocked, slot into AppLayout)"
tech_stack:
  added:
    - "@types/node (devDependency) — enables path module in vite.config.ts"
    - "shadcn/ui (base-nova style, neutral color, CSS variables)"
    - "@tanstack/react-table — required for BookDataTable in Plan 03"
    - "lucide-react (installed by shadcn init)"
    - "class-variance-authority, clsx, tailwind-merge (shadcn deps)"
  patterns:
    - "Nested Route element pattern for AppLayout shell wrapping"
    - "requireLibrarian prop for librarian-only route guard"
    - "useAuthStore (Zustand) consumed by AppLayout and NavBar"
key_files:
  created:
    - frontend/components.json
    - frontend/src/lib/utils.ts
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/input.tsx
    - frontend/src/components/ui/label.tsx
    - frontend/src/components/ui/table.tsx
    - frontend/src/components/ui/badge.tsx
    - frontend/src/components/ui/dialog.tsx
    - frontend/src/components/ui/card.tsx
    - frontend/src/components/ui/separator.tsx
    - frontend/src/components/ui/skeleton.tsx
    - frontend/src/components/ui/alert.tsx
    - frontend/src/components/AppLayout.tsx
    - frontend/src/components/NavBar.tsx
    - backend/alembic/versions/0003_catalog_indexes.py
  modified:
    - frontend/package.json
    - frontend/vite.config.ts
    - frontend/tsconfig.json
    - frontend/src/index.css
    - frontend/src/App.tsx
decisions:
  - "shadcn v4 uses 'base-nova' style (replaces v3 'New York') — accepted as equivalent default"
  - "AppLayout uses requireLibrarian prop pattern (not separate LibrarianLayout) for clean RSC-compatible composition"
  - "Stub placeholder divs used for catalog/librarian routes — Plan 03 replaces them with real components"
metrics:
  duration: "~20 minutes"
  completed: "2026-06-09"
  tasks_completed: 3
  files_created: 15
  files_modified: 5
---

# Phase 2 Plan 01: Dev Infrastructure — shadcn Init, Path Alias, Nav Shell, Alembic 0003 Summary

**One-liner:** shadcn/ui initialized with @/* alias, authenticated AppLayout+NavBar shell wired into App.tsx with role guards, and Alembic 0003 adds books title/author search indexes.

## What Was Built

### Task 1: @/* Path Alias + shadcn/ui Init

- Added `@types/node` devDependency to enable `path` module in `vite.config.ts`
- Updated `vite.config.ts` with `resolve.alias` mapping `@` to `./src` (runtime resolution)
- Updated `tsconfig.json` with `baseUrl: "."` and `paths: { "@/*": ["./src/*"] }` (TypeScript type resolution)
- Ran `npx shadcn@latest init` (base-nova style, neutral color, CSS variables enabled)
- Added 10 shadcn/ui components: button, input, label, table, badge, dialog, card, separator, skeleton, alert
- Installed `@tanstack/react-table` for BookDataTable (Plan 03)
- Verified: `npx tsc --noEmit` exits 0

### Task 2: AppLayout and NavBar Components

- **NavBar** (`frontend/src/components/NavBar.tsx`): h-14 top bar, white background, gray border-b. Logo link on left, role-aware nav links (all users see Catalog; librarians additionally see Manage Books), active link blue underline with border-b-2, logout button on right that clears auth store and navigates to /login.
- **AppLayout** (`frontend/src/components/AppLayout.tsx`): Auth guard redirects unauthenticated to `/login`, role guard redirects non-librarians attempting librarian routes to `/catalog`. Renders `<NavBar />` + `<main><Outlet /></main>` inside a `min-h-screen bg-gray-50` container.

### Task 3: App.tsx Route Wiring + Alembic 0003

- **App.tsx**: Public auth routes remain outside AppLayout. `/catalog` wrapped in `<Route element={<AppLayout />}>`. Librarian routes (`/librarian/books`, `/librarian/books/new`, `/librarian/books/:id`) wrapped in `<Route element={<AppLayout requireLibrarian />}>`. Stub placeholder divs used for catalog/librarian pages — Plan 03 replaces them.
- **Alembic 0003** (`backend/alembic/versions/0003_catalog_indexes.py`): Chains from 0002. `upgrade()` creates `ix_books_title` and `ix_books_author` on the `books` table. `downgrade()` drops both indexes in reverse order.

## Verification Results

- `npx tsc --noEmit` exits 0 after all changes
- All 10 shadcn components present at `frontend/src/components/ui/`
- `frontend/components.json` created by shadcn init
- `backend/alembic/versions/0003_catalog_indexes.py` has `down_revision = "0002"`
- Route structure in place: public routes outside shell, authenticated/librarian routes inside AppLayout

## Deviations from Plan

### Style Naming Change

**1. [Rule 1 - Deviation] shadcn v4 uses "base-nova" instead of "New York" style**
- **Found during:** Task 1
- **Issue:** The plan specified "New York" style (shadcn v3 name). shadcn v4 (4.11.0) renamed the style to "base-nova" as the default.
- **Fix:** Accepted base-nova as equivalent — it is the current standard default and provides the same component aesthetics. The `--defaults` flag used with `npx shadcn@latest init` correctly selects this.
- **Files modified:** `frontend/components.json` (style field)

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 | 511c545 | chore(02-01): configure @/* path alias and initialize shadcn/ui |
| 2 | bd39db8 | feat(02-01): add AppLayout and NavBar authenticated shell components |
| 3 | bb80b97 | feat(02-01): wire catalog routes in App.tsx and add Alembic migration 0003 |

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `<div>Catalog coming soon</div>` | frontend/src/App.tsx | ~38 | Plan 03 will replace with CatalogPage component |
| `<div>Manage Books coming soon</div>` | frontend/src/App.tsx | ~43 | Plan 03/future plan will replace with BookListPage |
| `<div>Add Book coming soon</div>` | frontend/src/App.tsx | ~44 | Plan 03/future plan will replace with AddBookPage |
| `<div>Book Detail coming soon</div>` | frontend/src/App.tsx | ~45 | Plan 03/future plan will replace with BookDetailPage |

These stubs are intentional — the routing structure is established so Plan 03 pages can slot in without changing routing.

## Self-Check: PASSED

- `frontend/src/components/AppLayout.tsx` — FOUND
- `frontend/src/components/NavBar.tsx` — FOUND
- `frontend/src/components/ui/button.tsx` — FOUND (all 10 components present)
- `frontend/components.json` — FOUND
- `backend/alembic/versions/0003_catalog_indexes.py` — FOUND
- Commits 511c545, bd39db8, bb80b97 — FOUND in git log
