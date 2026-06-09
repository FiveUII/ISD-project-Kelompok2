---
phase: 04-fines-notifications
plan: "01"
subsystem: database
tags: [fine, alembic, sqlalchemy, pydantic, decimal-arithmetic]

requires:
  - phase: 03-loans-circulation
    provides: Loan model, return_loan() endpoint, loans table

provides:
  - Fine SQLAlchemy ORM model (fines table)
  - Alembic migration 0006 creating fines table
  - FineResponse and WaiveRequest Pydantic schemas
  - return_loan() auto-creates Fine on overdue return using fine_rate_per_day from library_settings

affects: [04-02-fines-management, 04-03-notifications]

tech-stack:
  added: []
  patterns:
    - "Fine amount uses Decimal arithmetic (math.ceil + Decimal multiplication) to avoid float precision errors with monetary values"
    - "Fine status lifecycle: unpaid (default on creation) -> paid | waived"
    - "Server-side-only fine calculation: amount derived from DB timestamps (due_date, returned_at), no client input (T-04-01 mitigated)"

key-files:
  created:
    - backend/app/models/fine.py
    - backend/alembic/versions/0006_fines_table.py
    - backend/app/schemas/fines.py
  modified:
    - backend/app/models/loan.py
    - backend/app/models/__init__.py
    - backend/app/routers/loans.py

key-decisions:
  - "math.ceil rounds partial overdue days up — one hour overdue = 1 day fine (plan spec)"
  - "Fine not created when days_overdue == 0 (guard at if days_overdue > 0) — prevents negative fines (T-04-03)"
  - "fine_rate_per_day loaded from library_settings row id=1; fallback to Decimal('0.25') if no settings row"
  - "Fine.loan_id FK uses ondelete=RESTRICT — preserves fine history if loan deletion is ever attempted"
  - "WaiveRequest.reason validator strips whitespace and rejects empty strings (T-04-05)"

requirements-completed:
  - FINE-01

duration: 18min
completed: 2026-06-09
---

# Phase 04 Plan 01: Fine Auto-Calculation on Overdue Return Summary

**Fine SQLAlchemy model with Alembic migration 0006, FineResponse/WaiveRequest Pydantic schemas, and return_loan() extended to auto-create fine records using Decimal arithmetic when a loan is overdue**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-09T12:20:00Z
- **Completed:** 2026-06-09T12:38:00Z
- **Tasks:** 2
- **Files modified:** 5 (3 new, 2 modified)

## Accomplishments

- Created `Fine` SQLAlchemy ORM model with all required columns (id, loan_id FK, amount, days_overdue, status, waiver_reason, created_at) and `loan` relationship back to Loan
- Added Alembic migration 0006 (down_revision="0005") creating the fines table with ix_fines_loan_id index
- Created `backend/app/schemas/fines.py` with `FineResponse` (from_attributes=True) and `WaiveRequest` with non-empty reason validator
- Extended `return_loan()` to compute `days_overdue = math.ceil(seconds_overdue / 86400)` and create a Fine record when `days_overdue > 0` using `fine_rate_per_day` from library_settings
- Non-overdue returns are completely unaffected — LoanResponse signature unchanged

## Task Commits

1. **Task 04-01-T01: Fine model, migration, schemas** - `5af158e` (feat)
2. **Task 04-01-T02: Fine auto-calculation in return_loan()** - `669dfd7` (feat)

## Files Created/Modified

- `backend/app/models/fine.py` — Fine ORM model, fines table, loan relationship
- `backend/alembic/versions/0006_fines_table.py` — migration 0005→0006 (fines table)
- `backend/app/schemas/fines.py` — FineResponse + WaiveRequest Pydantic v2 schemas
- `backend/app/models/loan.py` — added `fines: Mapped[list["Fine"]]` relationship
- `backend/app/models/__init__.py` — registered `Fine` for Alembic autogenerate
- `backend/app/routers/loans.py` — imports `math`, `Decimal`, `Fine`; return_loan() extended with fine auto-creation

## Decisions Made

- Used `math.ceil` so a 1-hour overdue return costs 1 full day fine (plan spec)
- `fine_rate_per_day` always loaded from `library_settings` (id=1); no hardcoded rate anywhere
- `Fine` committed to session with `session.add(fine)` before `session.flush()` — ensures fine is persisted in the same transaction as the return
- `WaiveRequest.reason` validator strips whitespace and raises ValueError for blank strings (T-04-05) — plan specifies this at schema level

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Fine data layer is complete: model, migration, schemas all in place
- `return_loan()` will auto-create Fine rows on overdue returns once migration 0006 is applied
- Plan 04-02 can now build the fines API (GET list, PATCH /pay, PATCH /waive) and librarian fines UI

## Self-Check: PASSED

- [x] `backend/app/models/fine.py` exists with `class Fine(Base)` and `__tablename__ = "fines"`
- [x] `backend/app/models/loan.py` contains `fines: Mapped[list["Fine"]]` relationship
- [x] `backend/app/models/__init__.py` contains `from app.models.fine import Fine`
- [x] `backend/alembic/versions/0006_fines_table.py` exists with `revision = "0006"` and `down_revision = "0005"`
- [x] `backend/app/schemas/fines.py` exists with `class FineResponse(BaseModel)`
- [x] `backend/app/routers/loans.py` imports `math`, `Decimal`, and `Fine`
- [x] `return_loan()` contains `days_overdue` computation guarded by `if days_overdue > 0: ... Fine(...)`
- [x] All Python files pass `ast.parse()` syntax check

---
*Phase: 04-fines-notifications*
*Completed: 2026-06-09*
