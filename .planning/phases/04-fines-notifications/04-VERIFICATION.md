---
phase: 04-fines-notifications
status: human_needed
verified: 2026-06-09
must_haves_total: 5
must_haves_verified: 5
automated_checks: passed
human_verification:
  - "Complete overdue return → fine creation → pay/waive flow in running Docker stack"
  - "Verify APScheduler notification logs appear on Docker startup"
---

# Phase 04: Fines & Notifications — Verification Report

**Phase goal:** Overdue fines are calculated and tracked automatically on return; librarians can record payments and waivers; students receive proactive email reminders before and after due dates.

**Requirements:** FINE-01, FINE-02, FINE-03, NOTIF-01, NOTIF-02

---

## Automated Verification: PASSED

### Must-Have Checks

**FINE-01 — System auto-calculates fine on overdue return**
- `backend/app/routers/loans.py` → `PATCH /api/librarian/loans/{loan_id}/return` — fine creation block ✓
- `math.ceil((returned_at - due_date).total_seconds() / 86400)` — partial-day ceiling rounding ✓
- Fine rate loaded from `library_settings.fine_rate_per_day` with `Decimal("0.25")` fallback ✓
- `Fine(loan_id=loan.id, amount=fine_rate * days_overdue, days_overdue=days_overdue)` added to session ✓
- No fine created when returned on time (`days_overdue == 0`) ✓
- Fine amount uses `Decimal` arithmetic throughout — no float precision errors ✓

**FINE-02 — Librarian can mark a fine as paid**
- `backend/app/routers/fines.py` → `PATCH /api/librarian/fines/{fine_id}/pay` exists ✓
- 404 if fine not found ✓
- 409 Conflict if `fine.status != "unpaid"` (T-04-06 double-settle guard) ✓
- Sets `fine.status = "paid"`, reloads and returns `FineDetailResponse` ✓
- Protected by `require_librarian` via router-level dependency ✓

**FINE-03 — Librarian can waive a fine with reason**
- `backend/app/routers/fines.py` → `PATCH /api/librarian/fines/{fine_id}/waive` exists ✓
- Body: `WaiveRequest` with `field_validator` rejecting blank/whitespace reasons (T-04-05) ✓
- 409 Conflict if fine already settled (T-04-06) ✓
- Sets `fine.status = "waived"`, `fine.waiver_reason = data.reason` ✓
- Protected by `require_librarian` at router level ✓

**NOTIF-01 — Due-date reminder emails sent before due date**
- `backend/app/services/notification_service.py` → `run_notification_job()` ✓
- Queries `Loan.returned_at IS NULL, reminder_sent_at IS NULL, due_date >= now, due_date <= now + reminder_days_before days` ✓
- Calls `send_due_date_reminder(email, book_title, due_date)` per candidate ✓
- Sets `loan.reminder_sent_at = now` before commit — dedup flag prevents resend (T-04-08) ✓
- `reminder_days_before` loaded from `library_settings` with default 1 if no row ✓

**NOTIF-02 — Overdue alert emails sent when loan passes due date**
- Same `run_notification_job()` function ✓
- Queries `Loan.returned_at IS NULL, overdue_sent_at IS NULL, due_date < now` ✓
- Calls `send_overdue_alert(email, book_title, due_date)` per candidate ✓
- Sets `loan.overdue_sent_at = now` before commit — dedup flag prevents resend (T-04-08) ✓

### Build and Compile Checks
- `frontend/node_modules/.bin/tsc --noEmit` — PASSED ✓
- `python -m pytest tests/ -q` — 101 passed, 1 warning (pre-existing pydantic field shadow) ✓
- `python -c "import ast; ast.parse(open('backend/app/scheduler.py').read())"` — PASSED ✓
- `python -c "import ast; ast.parse(open('backend/app/routers/fines.py').read())"` — PASSED ✓
- `python -c "import ast; ast.parse(open('backend/app/services/notification_service.py').read())"` — PASSED ✓

### Key File Existence
- `backend/app/models/fine.py` ✓
- `backend/alembic/versions/0006_fines_table.py` (revision=0006, down_revision=0005) ✓
- `backend/alembic/versions/0007_loan_notification_sent_flags.py` (revision=0007, down_revision=0006) ✓
- `backend/app/routers/fines.py` ✓
- `backend/app/schemas/fines.py` ✓
- `backend/app/services/notification_service.py` ✓
- `backend/app/scheduler.py` ✓
- `frontend/src/pages/LibrarianFinesPage.tsx` ✓
- `frontend/src/api/fines.ts` ✓

### Schema and Wiring Checks
- `backend/app/models/__init__.py` imports `Fine` ✓
- `backend/app/main.py` includes `fines_router`, `configure_scheduler()`, `run_notification_job()` ✓
- `frontend/src/App.tsx` route `/librarian/fines` → `LibrarianFinesPage` ✓
- `frontend/src/components/NavBar.tsx` Fines link for librarian role ✓

### Code Review Fixes Applied (WR-01, WR-02, WR-03)
- WR-01: `AsyncIOScheduler` instantiated inside `configure_scheduler()` — no module-level global ✓
- WR-02: `status_filter` typed as `Literal["unpaid", "paid", "waived"] | None` — FastAPI validates at 422 ✓
- WR-03: Comment in `return_loan()` renumbered — step 5 now correctly labeled `# 5.` ✓

---

## Human Verification Required

All automated checks pass. The following items require testing in the running Docker Compose stack:

### Setup
```bash
docker compose up
# In a separate terminal:
docker compose exec api alembic upgrade head
```
Apply migrations 0006 (fines table) and 0007 (notification columns) if not yet applied.

### 1. Auto-Fine on Overdue Return
- Log in as librarian
- Set a loan's due_date to the past:
  ```sql
  docker compose exec db psql -U postgres -d librarydb -c \
    "UPDATE loans SET due_date = NOW() - INTERVAL '3 days' WHERE returned_at IS NULL LIMIT 1 RETURNING id, due_date;"
  ```
- In LibrarianLoansPage → Overdue Loans tab: click Return on that loan
- Navigate to /librarian/fines → verify a new fine appears with `days_overdue=3`, correct `amount` (3 × daily_rate), `status=unpaid`

### 2. Pay a Fine
- On LibrarianFinesPage, find an unpaid fine → click Pay button
- Verify ConfirmDialog appears → click Confirm
- Verify fine status badge changes to green "Paid"
- Verify Pay/Waive buttons disappear for that fine

### 3. Waive a Fine
- On LibrarianFinesPage, find another unpaid fine → click Waive button
- Verify dialog opens with reason textarea
- Submit with an empty reason → verify submit button is disabled or error appears
- Enter a reason ("Student returned due to illness") → click Waive
- Verify fine status badge changes to yellow "Waived"

### 4. Notification Job Startup Logs
- In `docker compose logs api` output, look for:
  ```
  Notification job completed: X reminder(s), Y overdue alert(s) sent
  ```
  (This fires once at startup via `asyncio.ensure_future`)
- If any overdue loans with `overdue_sent_at IS NULL` exist, look for:
  ```
  OVERDUE ALERT (dev): to=<email> book='...' due=...
  ```

### 5. Due-Date Reminder (optional — requires loan due within 1 day)
```sql
docker compose exec db psql -U postgres -d librarydb -c \
  "UPDATE loans SET due_date = NOW() + INTERVAL '12 hours', reminder_sent_at = NULL WHERE returned_at IS NULL LIMIT 1;"
```
Restart the API container: `docker compose restart api`
- Check logs for:
  ```
  DUE DATE REMINDER (dev): to=<email> book='...' due=...
  ```

### 6. Double-Settle Guard
- Attempt to pay a fine already marked paid:
  ```bash
  curl -X PATCH http://localhost/api/librarian/fines/<id>/pay -H "Authorization: Bearer <token>"
  ```
- Verify 409 Conflict response: `{"detail": "Fine already settled"}`

---

## Code Review Results

`04-REVIEW.md` written. No critical issues. 3 warnings resolved before commit:
- WR-01: Module-level `AsyncIOScheduler` global → moved inside `configure_scheduler()` (fixed)
- WR-02: `status_filter` accepted arbitrary strings → now typed `Literal["unpaid","paid","waived"]` (fixed)
- WR-03: Duplicate `# 4.` comment in `return_loan()` → renumbered to `# 5.` (fixed)

---

## v1 MVP Status

Phase 4 is the final phase. All v1 requirements are implemented:

| Group | Requirements | Status |
|-------|-------------|--------|
| Auth | AUTH-01 to AUTH-04 | Complete (Phase 1) |
| Catalog | CATL-01 to CATL-06, CATS-01, CATS-02 | Complete (Phase 2) |
| Loans | LOAN-01 to LOAN-06 | Complete (Phase 3) |
| Fines | FINE-01 to FINE-03 | Complete (Phase 4) |
| Notifications | NOTIF-01 to NOTIF-02 | Complete (Phase 4) |

The full stack (`docker compose up`) delivers the complete v1 Library Management System.
