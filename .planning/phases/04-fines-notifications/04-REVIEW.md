---
phase: 04-fines-notifications
status: warnings
depth: standard
files_reviewed: 17
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
reviewed: 2026-06-09
---

# Phase 04: Fines & Notifications — Code Review

**Depth:** standard
**Files reviewed:** 17
**Status:** warnings (0 critical, 3 warning, 2 info)

---

## Summary

Phase 4 implements the fines ledger and APScheduler-based email notifications. The core logic is correct and well-structured — RBAC is enforced at the router level, fine amounts use Decimal arithmetic, and deduplication flags prevent duplicate email sends. Three warnings merit attention before UAT or production use.

---

## Findings

### WR-01 — `scheduler` module-level global shared across `configure_scheduler()` calls

**Severity:** Warning
**File:** `backend/app/scheduler.py` (line 18)
**Category:** Bug / Correctness

**Issue:** `scheduler = AsyncIOScheduler(misfire_grace_time=3600)` is instantiated at module import time as a global. `configure_scheduler()` calls `scheduler.add_job(...)` on this global instance. If the module is imported multiple times (e.g., during test setup or hot-reload), `add_job` will be called on an already-configured scheduler, potentially adding duplicate `daily_notifications` jobs or attempting to add a job to a running scheduler.

**Recommendation:** Instantiate the scheduler inside `configure_scheduler()` and return it:
```python
def configure_scheduler() -> AsyncIOScheduler:
    _scheduler = AsyncIOScheduler(misfire_grace_time=3600)
    _scheduler.add_job(
        run_notification_job,
        "interval",
        hours=24,
        id="daily_notifications",
    )
    return _scheduler
```
This makes each call idempotent and avoids the module-level mutable state.

---

### WR-02 — `status_filter` in `list_fines` accepts arbitrary string — no enum validation

**Severity:** Warning
**File:** `backend/app/routers/fines.py` (line 69)
**Category:** Input Validation

**Issue:** `status_filter: str | None = Query(None, alias="status")` accepts any string. A request with `?status=unknown` will silently return 0 results without informing the caller that the value is invalid. The valid values are `unpaid`, `paid`, `waived`.

**Recommendation:** Use a `Literal` or `Enum` type annotation:
```python
from typing import Literal
status_filter: Literal["unpaid", "paid", "waived"] | None = Query(None, alias="status")
```
FastAPI will then return 422 for invalid status values with a clear error message.

---

### WR-03 — `return_loan()` comment numbering error (minor readability)

**Severity:** Warning (minor)
**File:** `backend/app/routers/loans.py` (line 220)
**Category:** Code Quality

**Issue:** The comment at line 220 reads `# 4. Reload with fresh relationships for response` but there is already a `# 4.` at line 191 (`# 4. Auto-calculate fine for overdue returns`). Two consecutive steps are labelled `4.`. This is cosmetic but causes confusion when tracing the code flow.

**Recommendation:** Renumber the reload step as `# 5. Reload with fresh relationships for response`.

---

### INFO-01 — `_fine_to_detail` mutates ORM object in place (`fine.loan.book = ...`)

**Severity:** Info
**File:** `backend/app/routers/fines.py` (line 58)
**Category:** Code Smell

**Note:** `fine.loan.book = fine.loan.copy.book` mutates the in-memory ORM object to add a synthetic attribute. This is the established pattern from `_loan_to_response` in `loans.py` and works correctly with SQLAlchemy's lazy attribute handling. It is documented and consistent. The only risk is if `fine.loan.book` ever conflicts with a real SQLAlchemy relationship on the `Loan` model — currently it doesn't since `Loan` has no direct `book` relationship. No action required but worth noting for future model evolution.

---

### INFO-02 — `run_notification_job` catches all exceptions silently at the top level

**Severity:** Info
**File:** `backend/app/services/notification_service.py` (lines 37, 109)
**Category:** Observability

**Note:** The broad `except Exception: logger.exception(...)` at the top level is intentional (T-04-09 mitigated) and correctly prevents scheduler crashes. However, individual loan notification failures inside the loop are not isolated — if `send_due_date_reminder` raises for one loan, the entire batch fails. For v1 dev logging this is acceptable (all sends are stdout), but when real SMTP is added a per-loan try/except would prevent one bad email from blocking the rest of the batch. No action required for v1.

---

## Files Reviewed

| File | Status |
|------|--------|
| backend/alembic/versions/0006_fines_table.py | Clean |
| backend/alembic/versions/0007_loan_notification_sent_flags.py | Clean |
| backend/app/main.py | Clean |
| backend/app/models/__init__.py | Clean |
| backend/app/models/fine.py | Clean |
| backend/app/models/loan.py | Clean |
| backend/app/routers/fines.py | WR-01 candidate, WR-02 |
| backend/app/routers/loans.py | WR-03 |
| backend/app/scheduler.py | WR-01 |
| backend/app/schemas/fines.py | Clean |
| backend/app/services/email_service.py | Clean |
| backend/app/services/notification_service.py | INFO-02 |
| backend/requirements.txt | Clean |
| frontend/src/App.tsx | Clean |
| frontend/src/api/fines.ts | Clean |
| frontend/src/components/NavBar.tsx | Clean |
| frontend/src/pages/LibrarianFinesPage.tsx | Clean |

---

## Security Assessment

- RBAC enforced at router level for all fines endpoints (`dependencies=[Depends(require_librarian)]`) — T-04-04 ✓
- Fine amounts computed entirely server-side from DB timestamps — no client input into amount — T-04-01 ✓
- WaiveRequest.reason field_validator rejects blank strings — T-04-05 ✓
- 409 guard prevents double-payment/double-waiver — T-04-06 ✓
- reminder_sent_at/overdue_sent_at flags prevent duplicate email sends — T-04-08 ✓
- Notification job wrapped in try/except — T-04-09 ✓
- No hardcoded fine rates — loaded from library_settings with Decimal fallback ✓
