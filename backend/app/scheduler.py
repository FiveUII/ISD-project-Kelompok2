"""
APScheduler configuration for the Library Management System.

Configures a daily notification job that checks for loans needing
due-date reminders or overdue alerts.

In-process scheduler (AsyncIOScheduler) — runs inside the FastAPI container.
No separate worker container or broker required for v1 scope.
(STATE.md blocker resolved: APScheduler in-process is the correct v1 pattern.)

Misfire grace time: 3600s — missed jobs are skipped (not accumulated) after
downtime, acceptable for daily email reminders (T-04-10 mitigated).
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.notification_service import run_notification_job

scheduler = AsyncIOScheduler(misfire_grace_time=3600)


def configure_scheduler() -> AsyncIOScheduler:
    """
    Add the daily notification job and return the configured scheduler.

    The scheduler is started/stopped in the FastAPI lifespan (main.py).
    Job fires at startup (via asyncio.ensure_future in lifespan) and then
    every 24 hours via the interval trigger.
    """
    scheduler.add_job(
        run_notification_job,
        "interval",
        hours=24,
        id="daily_notifications",
    )
    return scheduler
