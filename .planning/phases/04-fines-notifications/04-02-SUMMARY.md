---
phase: 04-fines-notifications
plan: "02"
subsystem: api
tags: [fines, fastapi, react, tanstack-query, tanstack-table, pydantic]

requires:
  - phase: 04-fines-notifications/04-01
    provides: Fine model, fines table, FineResponse schema, auto-creation on return

provides:
  - GET /api/librarian/fines (paginated, status filter, nested loan/borrower/book info)
  - PATCH /api/librarian/fines/{id}/pay (409 if already settled)
  - PATCH /api/librarian/fines/{id}/waive with reason (422 if blank, 409 if settled)
  - LibrarianFinesPage at /librarian/fines with Pay/Waive actions
  - NavBar Fines link for librarians

affects: [04-03-notifications]

tech-stack:
  added: []
  patterns:
    - "FINE_EAGER_OPTIONS selectinload pattern: Fine.loan -> Loan.borrower + Fine.loan -> Loan.copy -> Copy.book"
    - "_fine_to_detail() attaches fine.loan.book = fine.loan.copy.book (same pattern as _loan_to_response)"
    - "WaiveRequest.reason Pydantic field_validator rejects empty/whitespace strings at schema level"
    - "Waive dialog uses plain <textarea> with Tailwind styling (no shadcn Textarea component needed)"

key-files:
  created:
    - backend/app/routers/fines.py
    - frontend/src/api/fines.ts
    - frontend/src/pages/LibrarianFinesPage.tsx
  modified:
    - backend/app/schemas/fines.py
    - backend/app/main.py
    - frontend/src/components/NavBar.tsx
    - frontend/src/App.tsx

key-decisions:
  - "FinesListResponse uses status=Query(None, alias='status') to avoid shadowing the Python builtin 'status'"
  - "Pay/Waive buttons are disabled when fine.status != 'unpaid' — prevents UI-level double-settlement"
  - "Waive dialog submit disabled when waiveReason.trim() is empty — prevents empty reason reaching the API"
  - "Used plain <textarea> instead of creating a shadcn Textarea component — no additional component needed"

requirements-completed:
  - FINE-02
  - FINE-03

duration: 22min
completed: 2026-06-09
---

# Phase 04 Plan 02: Fine Management API + Librarian Fines UI Summary

**Fines management API (GET list, PATCH pay, PATCH waive) with FineDetailResponse including eager-loaded loan/borrower/book info, and LibrarianFinesPage React component with Pay/Waive actions, ConfirmDialog for payment, and reason-input Dialog for waivers**

## Performance

- **Duration:** 22 min
- **Started:** 2026-06-09T12:40:00Z
- **Completed:** 2026-06-09T13:02:00Z
- **Tasks:** 2
- **Files modified:** 7 (3 new, 4 modified)

## Accomplishments

- Created `backend/app/routers/fines.py` with three endpoints (GET list, PATCH /pay, PATCH /waive), all protected by `require_librarian` at router level (T-04-04)
- Extended `backend/app/schemas/fines.py` with `LoanBriefForFine`, `FineDetailResponse`, and `FinesListResponse` schemas
- Registered `fines_router` in `main.py` under `/api` prefix after loans router
- Created `frontend/src/api/fines.ts` with `getLibrarianFines`, `payFine`, and `waiveFine` typed client functions
- Created `LibrarianFinesPage` with TanStack Table, Pay (ConfirmDialog), Waive (Dialog + textarea), animated loading skeleton, and empty state
- Added Fines nav link in NavBar for librarian role; added `/librarian/fines` route in App.tsx requireLibrarian block
- Frontend TypeScript compiles clean; `npm run build` passes (459KB bundle)

## Task Commits

1. **Task 04-02-T01: Fines API router (list, pay, waive) + register in main.py** - `457b93d` (feat)
2. **Task 04-02-T02: LibrarianFinesPage + NavBar + App.tsx** - `ff3cd3f` (feat)

## Files Created/Modified

- `backend/app/routers/fines.py` — fines_router with GET, PATCH /pay, PATCH /waive endpoints
- `backend/app/schemas/fines.py` — extended with LoanBriefForFine, FineDetailResponse, FinesListResponse
- `backend/app/main.py` — imports fines module and includes fines_router
- `frontend/src/api/fines.ts` — getLibrarianFines, payFine, waiveFine API functions
- `frontend/src/pages/LibrarianFinesPage.tsx` — full fines management page
- `frontend/src/components/NavBar.tsx` — Fines link added for librarian role
- `frontend/src/App.tsx` — /librarian/fines route added to requireLibrarian block

## Decisions Made

- `status_filter` query param uses `Query(None, alias="status")` to avoid shadowing Python's `status` builtin
- Waive dialog uses a plain `<textarea>` with Tailwind classes rather than creating a new shadcn Textarea component — simpler and sufficient for the use case
- Pay and Waive action buttons are disabled when `fine.status !== 'unpaid'` in the UI, complementing the backend 409 guard

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Fines API and UI are complete. After running migration 0006, librarians can list fines and mark them paid or waived.
- Plan 04-03 can now safely add notification columns to the Loan model (migration 0007) and wire the APScheduler, since `main.py` is stable.

## Self-Check: PASSED

- [x] `backend/app/routers/fines.py` exists with GET /api/librarian/fines, PATCH pay, PATCH waive
- [x] `backend/app/main.py` contains `from app.routers import fines` and `app.include_router(fines.fines_router, prefix="/api")`
- [x] `frontend/src/api/fines.ts` exists with `getLibrarianFines`, `payFine`, `waiveFine` exports
- [x] `frontend/src/pages/LibrarianFinesPage.tsx` exists and imports from `@/api/fines`
- [x] `frontend/src/components/NavBar.tsx` contains `/librarian/fines` link inside librarian role block
- [x] `frontend/src/App.tsx` contains `path="/librarian/fines"` route in requireLibrarian block
- [x] `npx tsc --noEmit` passes (no output)
- [x] `npm run build` passes (459KB bundle, 3.99s)
- [x] All Python files pass `ast.parse()` syntax check

---
*Phase: 04-fines-notifications*
*Completed: 2026-06-09*
