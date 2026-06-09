---
phase: 03-loans-circulation
plan: "02"
subsystem: ui
tags: [react, tanstack-query, tanstack-table, typescript, loans, circulation, dialog]

requires:
  - phase: 03-loans-circulation-plan01
    provides: Loans API backend — checkout, return, list, and my-loans endpoints

provides:
  - frontend/src/api/loans.ts — API client functions for all loan operations
  - GET /api/admin/users?role=student&search= endpoint (backend deviation fix)
  - NavBar extended with "My Loans" (student) and "Loans" (librarian) links
  - LibrarianLoansPage — Active/Overdue tabs, Return action with ConfirmDialog, TanStack Table
  - BookDetailPage — "Check Out" button on available copies (librarian only), checkout modal with student search

affects: [03-loans-circulation-plan03]

tech-stack:
  added: []
  patterns:
    - "Dialog import from @/components/ui/dialog (base-ui/react) — not shadcn Radix version"
    - "Loans API client in frontend/src/api/ directory (new directory pattern for dedicated API modules)"
    - "getMyLoans() exported from loans.ts for Plan 03 MyLoansPage consumption"

key-files:
  created:
    - frontend/src/api/loans.ts
    - frontend/src/pages/LibrarianLoansPage.tsx
  modified:
    - frontend/src/components/NavBar.tsx
    - frontend/src/App.tsx
    - frontend/src/pages/BookDetailPage.tsx
    - backend/app/routers/admin.py

key-decisions:
  - "Added GET /api/admin/users endpoint to admin router as deviation — plan referenced it but it didn't exist; protected by require_admin (librarian admin only)"
  - "Checkout Dialog controlled by checkoutCopyId state (null = closed); avoids separate boolean open state"
  - "Student search dropdown shown only when query >= 2 chars AND no student selected yet"
  - "approxDueDate computed client-side as today+14 days with note that server uses library_settings"

requirements-completed: [LOAN-01, LOAN-02, LOAN-05, LOAN-06]

duration: 22min
completed: 2026-06-09
---

# Phase 03 Plan 02: Frontend Librarian Loans UI Summary

**React loans dashboard with Active/Overdue tabs, row-level Return action with ConfirmDialog, and checkout modal on Book Detail with student search-as-you-type**

## Performance

- **Duration:** 22 min
- **Started:** 2026-06-09T11:26:00Z
- **Completed:** 2026-06-09T11:48:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Created `frontend/src/api/loans.ts` with getLibrarianLoans, returnLoan, checkoutCopy, searchStudents, getMyLoans functions
- LibrarianLoansPage with Active/Overdue tab state, TanStack Table v8 loan columns, Return mutation with ConfirmDialog invalidating `['librarian-loans']`
- BookDetailPage extended with checkout modal — student search, selected student display, approximate due date, Confirm Checkout button
- NavBar now shows "My Loans" for students and "Loans" for librarians
- TypeScript compiles clean; npm run build passes

## Task Commits

1. **Task deviation: GET /api/admin/users student search endpoint** - `040e46a` (feat)
2. **Task 1: Loans API client + NavBar + App.tsx** - `1c6d1aa` (feat)
3. **Task 2: LibrarianLoansPage** - `cd302c6` (feat)
4. **Task 3: Checkout modal on BookDetailPage** - `be53aa9` (feat)

## Files Created/Modified
- `frontend/src/api/loans.ts` — LoanItem/LoansListResponse/StudentUser types, getLibrarianLoans/returnLoan/checkoutCopy/searchStudents/getMyLoans
- `frontend/src/pages/LibrarianLoansPage.tsx` — Active/Overdue tabs, TanStack Table v8, Return with ConfirmDialog
- `frontend/src/pages/BookDetailPage.tsx` — Check Out button (librarian+available only), Dialog checkout modal with student typeahead
- `frontend/src/components/NavBar.tsx` — My Loans link (student), Loans link (librarian)
- `frontend/src/App.tsx` — /librarian/loans route in requireLibrarian block
- `backend/app/routers/admin.py` — GET /api/admin/users with role+search params (deviation)

## Decisions Made
- Dialog controlled via `checkoutCopyId` state: `null` = closed, number = open — avoids separate boolean tracking
- Student search shows dropdown only while query >= 2 chars AND no student is selected yet
- Approximate due date shown client-side (today+14 days) with a note; actual due date returned by POST /checkout may differ

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added GET /api/admin/users endpoint to backend**
- **Found during:** Task 1 (reading backend/app/routers/admin.py)
- **Issue:** Plan referenced `GET /api/admin/users?role=student&search=query` but no such endpoint existed — only POST /promote was present
- **Fix:** Added list_users endpoint to admin router with role and search filters, ILIKE matching, limit 20
- **Files modified:** backend/app/routers/admin.py
- **Verification:** python -m py_compile passes; endpoint returns correct filtered user list
- **Committed in:** 040e46a

---

**Total deviations:** 1 auto-fixed (1 missing critical endpoint)
**Impact on plan:** Required for student search in checkout modal; no scope creep — endpoint was implied by plan's searchStudents function.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 02 librarian UI complete; Plan 03 can now build MyLoansPage using getMyLoans() from loans.ts
- App.tsx /my-loans route needs to be added in Plan 03 (non-requireLibrarian AppLayout block)

---
*Phase: 03-loans-circulation*
*Completed: 2026-06-09*

## Self-Check: PASSED
- frontend/src/api/loans.ts exists with getLibrarianLoans, returnLoan, checkoutCopy, searchStudents ✓
- NavBar shows "My Loans" for students at /my-loans and "Loans" for librarians at /librarian/loans ✓
- App.tsx has /librarian/loans route inside requireLibrarian AppLayout block ✓
- LibrarianLoansPage renders Active Loans and Overdue Loans tabs ✓
- Loans table has Student, Book, Copy, Due date, Status badge, Return button columns ✓
- Return action calls PATCH /api/librarian/loans/{id}/return and invalidates ['librarian-loans'] ✓
- Return action wrapped in ConfirmDialog ✓
- BookDetailPage shows "Check Out" button on available copies (librarian only) ✓
- Checkout modal has student search-as-you-type, selected student display, approximate due date, Confirm Checkout button ✓
- npx tsc --noEmit passes ✓
- npm run build passes ✓
