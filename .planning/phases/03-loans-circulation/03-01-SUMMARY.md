---
phase: 03-loans-circulation
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, alembic, pydantic, loans, circulation]

requires:
  - phase: 02-catalog
    provides: Copy model with CopyStatus enum, LibrarySettings model with loan_period_days, User model with UserRole enum, dependencies.py with get_current_user/require_librarian

provides:
  - Loan SQLAlchemy ORM model (loans table) with copy_id, user_id, checked_out_at, due_date, returned_at
  - Alembic migration 0005 creating the loans table with FK constraints and indexes
  - Pydantic v2 schemas: CheckoutRequest, LoanResponse (with is_overdue computed field), LoansListResponse
  - POST /api/librarian/loans/checkout — validates copy availability (409) and student role (400), calculates due_date from library_settings
  - PATCH /api/librarian/loans/{loan_id}/return — sets returned_at, restores copy status, 409 if already returned
  - GET /api/librarian/loans?overdue=true — active loans list with computed overdue filter
  - GET /api/loans/my — authenticated student's active loans (user_id from JWT sub only)

affects: [03-loans-circulation-plan02, 03-loans-circulation-plan03]

tech-stack:
  added: []
  patterns:
    - "Overdue flag computed at query time (due_date < now() AND returned_at IS NULL) — no stored status column, no background job (D-01)"
    - "RBAC enforced at router level via dependencies=[Depends(require_librarian)] — no inline role checks"
    - "loan_period_days always read from library_settings row (id=1) — never hardcoded (D-04)"
    - "book field attached directly to loan instance before model_validate() for Pydantic nested schema mapping"

key-files:
  created:
    - backend/app/models/loan.py
    - backend/alembic/versions/0005_loans_table.py
    - backend/app/schemas/loans.py
    - backend/app/routers/loans.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/models/copy.py
    - backend/app/models/user.py
    - backend/app/main.py

key-decisions:
  - "Loan.book mapped via _loan_to_response() helper that attaches loan.copy.book as loan.book before Pydantic model_validate — avoids a custom validator in the schema"
  - "session.flush() before reload after checkout to get loan.id; then re-query with selectinload for full relationships"
  - "GET /api/librarian/loans uses single base_filter list for both active and overdue filters, avoiding dual select() branches"

requirements-completed: [LOAN-01, LOAN-02, LOAN-03, LOAN-05, LOAN-06]

duration: 18min
completed: 2026-06-09
---

# Phase 03 Plan 01: Backend Loans API Summary

**FastAPI loans router with checkout (409/400 guards), return (409 idempotency), and list/overdue query — backed by Loan ORM model, Alembic migration 0005, and Pydantic v2 schemas with computed is_overdue field**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-09T11:07:33Z
- **Completed:** 2026-06-09T11:25:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Created Loan SQLAlchemy ORM model with proper FK constraints, indexes, and back_populates relationships on Copy and User
- Added Alembic migration 0005 (manual — no Docker-based autogenerate) creating the loans table
- Created Pydantic v2 schemas with `@computed_field` for is_overdue (due_date < now() AND returned_at is None)
- Implemented full loans router: checkout validates availability+role, return is idempotent, list supports overdue filter, student /my endpoint uses JWT sub

## Task Commits

Each task was committed atomically:

1. **Task 1: Loan ORM model and Alembic migration 0005** - `1f288ef` (feat)
2. **Task 2: Pydantic v2 loan schemas** - `4d9397b` (feat)
3. **Task 3: Loans FastAPI router and main.py registration** - `57a3475` (feat)

## Files Created/Modified
- `backend/app/models/loan.py` — Loan ORM model: id, copy_id, user_id, checked_out_at, due_date, returned_at, relationships to Copy and User
- `backend/alembic/versions/0005_loans_table.py` — Migration creating loans table with FK constraints, copy_id and user_id indexes
- `backend/app/schemas/loans.py` — CheckoutRequest, LoanResponse (with @computed_field is_overdue), nested brief schemas, LoansListResponse
- `backend/app/routers/loans.py` — loans_router (/librarian/loans) and student_loans_router (/loans)
- `backend/app/models/__init__.py` — Added Loan import for Alembic autogenerate discovery
- `backend/app/models/copy.py` — Added loans relationship back_populates
- `backend/app/models/user.py` — Added loans relationship back_populates
- `backend/app/main.py` — Registered both loans routers under /api prefix

## Decisions Made
- Used `session.flush()` + re-query with selectinload after checkout to get both the generated loan.id and fully eager-loaded relationships in one pass, avoiding a second round-trip after commit
- Implemented `_loan_to_response()` helper that attaches `loan.copy.book` as `loan.book` on the ORM instance before calling `LoanResponse.model_validate()` — Pydantic needs a direct attribute for nested field mapping
- `GET /api/librarian/loans` base_filter as a list appended conditionally, keeping overdue and active-only paths in one query builder

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All backend endpoints ready for frontend consumption (Plan 02)
- Plan 02 (frontend librarian slice) can now implement getLibrarianLoans, returnLoan, checkoutCopy
- Note: `GET /api/admin/users?role=student&search=query` for student search in the checkout modal does not yet exist — Plan 02 must add it to the admin router or create a new endpoint

---
*Phase: 03-loans-circulation*
*Completed: 2026-06-09*

## Self-Check: PASSED
- `backend/app/models/loan.py` exists with class Loan ✓
- `backend/app/models/__init__.py` imports Loan ✓
- `backend/alembic/versions/0005_loans_table.py` exists with op.create_table("loans"...) ✓
- `backend/app/schemas/loans.py` has CheckoutRequest, LoanResponse with @computed_field is_overdue, LoansListResponse ✓
- `backend/app/routers/loans.py` has loans_router (prefix=/librarian/loans) and student_loans_router (prefix=/loans) ✓
- POST checkout: 409 for non-available copy, 400 for non-student user, due_date from library_settings ✓
- PATCH return: sets returned_at, sets copy.status=available, 409 if already returned ✓
- GET /api/librarian/loans?overdue=true: filters due_date < now() AND returned_at IS NULL ✓
- GET /api/loans/my: user_id from JWT sub (get_current_user), never from query params ✓
- All Python files pass py_compile ✓
