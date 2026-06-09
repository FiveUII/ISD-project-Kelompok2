---
phase: 04-fines-notifications
plan: "03"
subsystem: infra
tags: [apscheduler, email, notifications, asyncio, alembic]

requires:
  - phase: 04-fines-notifications/04-02
    provides: stable main.py (fines router registered) before scheduler is wired in

provides:
  - Loan.reminder_sent_at and Loan.overdue_sent_at nullable DateTime columns
  - Alembic migration 0007 adding both columns to loans table
  - send_due_date_reminder() and send_overdue_alert() log functions in email_service.py
  - run_notification_job() async function that finds and emails reminder/overdue candidates
  - configure_scheduler() with AsyncIOScheduler (24h interval, misfire_grace_time=3600)
  - FastAPI lifespan wires scheduler start/stop + immediate startup fire

affects: []

tech-stack:
  added:
    - apscheduler>=3.10 (AsyncIOScheduler — in-process scheduler, no broker needed)
  patterns:
    - "In-process scheduler (AsyncIOScheduler) inside FastAPI container — no separate worker or broker for v1 scope"
    - "asyncio.ensure_future(run_notification_job()) fires job once at startup without blocking lifespan yield"
    - "reminder_sent_at / overdue_sent_at flags prevent duplicate sends across scheduler runs (T-04-08)"
    - "Notification job wraps entire body in try/except Exception to prevent silent failures (T-04-09)"

key-files:
  created:
    - backend/app/services/notification_service.py
    - backend/app/scheduler.py
    - backend/alembic/versions/0007_loan_notification_sent_flags.py
  modified:
    - backend/app/services/email_service.py
    - backend/app/models/loan.py
    - backend/app/main.py
    - backend/requirements.txt

key-decisions:
  - "APScheduler runs in-process inside the FastAPI container (not a separate container) — resolves the STATE.md blocker about 'APScheduler + FastAPI separate-container integration'"
  - "asyncio.ensure_future() used for startup fire — non-blocking, job runs in background while lifespan yields"
  - "misfire_grace_time=3600 + in-memory job store: missed jobs are skipped after downtime, not accumulated (T-04-10)"
  - "Reminder query filters due_date >= now AND due_date <= (now + reminder_days_before days) — current loans only, not future"
  - "Notification job logs reminder_count + overdue_count after commit for operational visibility"

requirements-completed:
  - NOTIF-01
  - NOTIF-02

duration: 20min
completed: 2026-06-09
---

# Phase 04 Plan 03: APScheduler + Email Notification Service Summary

**In-process APScheduler with daily notification job: due-date reminders and overdue alerts logged to stdout, deduplicated via reminder_sent_at/overdue_sent_at timestamp flags on the Loan model, firing once at startup and every 24 hours thereafter**

## Performance

- **Duration:** 20 min
- **Started:** 2026-06-09T13:05:00Z
- **Completed:** 2026-06-09T13:25:00Z
- **Tasks:** 2
- **Files modified:** 7 (3 new, 4 modified)

## Accomplishments

- Added `reminder_sent_at` and `overdue_sent_at` nullable DateTime columns to the Loan model and created Alembic migration 0007 (down_revision="0006")
- Added `apscheduler>=3.10` to `backend/requirements.txt`
- Extended `email_service.py` with `send_due_date_reminder()` and `send_overdue_alert()` that log to stdout + logger
- Created `notification_service.py` with `run_notification_job()` — queries both candidate sets with selectinload eager-loading, sends emails, sets sent_at flags, commits, logs summary, wraps in try/except (T-04-09)
- Created `scheduler.py` with `configure_scheduler()` using `AsyncIOScheduler(misfire_grace_time=3600)` and a `daily_notifications` interval job
- Extended `main.py` lifespan: `configure_scheduler()` + `_scheduler.start()` + `asyncio.ensure_future(run_notification_job())` after yield `_scheduler.shutdown(wait=False)`

## Task Commits

1. **Task 04-03-T01: Notification columns + migration 0007 + apscheduler dep** - `0dac1e3` (feat)
2. **Task 04-03-T02: Notification service + scheduler + lifespan wiring** - `7d55aff` (feat)

## Files Created/Modified

- `backend/app/services/notification_service.py` — run_notification_job() async function
- `backend/app/scheduler.py` — configure_scheduler() with AsyncIOScheduler
- `backend/alembic/versions/0007_loan_notification_sent_flags.py` — migration 0006→0007
- `backend/app/services/email_service.py` — send_due_date_reminder() + send_overdue_alert()
- `backend/app/models/loan.py` — reminder_sent_at and overdue_sent_at columns
- `backend/app/main.py` — scheduler start/stop + startup fire in lifespan
- `backend/requirements.txt` — apscheduler>=3.10

## Decisions Made

- Used `asyncio.ensure_future()` for the startup notification fire rather than `await` — avoids blocking the lifespan yield, job runs concurrently
- In-process scheduler resolves the STATE.md concern about "APScheduler + FastAPI separate-container integration" — no Docker complexity for v1 scope
- `misfire_grace_time=3600` with in-memory job store: after downtime, missed daily jobs skip rather than accumulate (T-04-10 accepted)
- Try/except wraps the entire job body so a DB error doesn't silently kill the scheduler loop (T-04-09)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required (dev mode logs to stdout; no SMTP credentials needed).

## Next Phase Readiness

- All 5 requirements (FINE-01 through NOTIF-02) are now implemented across Plans 01-03
- Phase 4 is ready for Docker-based UAT: run `docker compose up`, apply migrations 0006+0007, create overdue loans, observe fine creation and notification logs
- APScheduler in-process resolves the STATE.md blocker from Phase 3 context

## Self-Check: PASSED

- [x] `backend/app/models/loan.py` contains `reminder_sent_at` and `overdue_sent_at` nullable DateTime columns
- [x] `backend/alembic/versions/0007_loan_notification_sent_flags.py` exists with `revision = "0007"` and `down_revision = "0006"`
- [x] `backend/requirements.txt` contains `apscheduler>=3.10`
- [x] `backend/app/services/email_service.py` contains `send_due_date_reminder` and `send_overdue_alert`
- [x] `backend/app/services/notification_service.py` exists with `run_notification_job` async function
- [x] `backend/app/scheduler.py` exists with `configure_scheduler()` returning `AsyncIOScheduler`
- [x] `backend/app/main.py` lifespan calls `configure_scheduler()`, `_scheduler.start()`, `asyncio.ensure_future(run_notification_job())`, and `_scheduler.shutdown(wait=False)` after yield
- [x] All Python files pass `ast.parse()` syntax check

---
*Phase: 04-fines-notifications*
*Completed: 2026-06-09*
