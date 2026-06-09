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


def configure_scheduler() -> AsyncIOScheduler:
    """
    Instantiate and configure a fresh AsyncIOScheduler with the daily notification job.

    Returns a new scheduler instance each call — avoids module-level mutable global
    that could accumulate duplicate jobs on re-import or hot-reload (WR-01 fix).

    The scheduler is started/stopped in the FastAPI lifespan (main.py).
    Job fires at startup (via asyncio.ensure_future in lifespan) and then
    every 24 hours via the interval trigger.
    """
    _scheduler = AsyncIOScheduler(misfire_grace_time=3600)
    _scheduler.add_job(
        run_notification_job,
        "interval",
        hours=24,
        id="daily_notifications",
    )
    return _scheduler
