"""
Notification service — runs the daily loan notification job.

Called by APScheduler in backend/app/scheduler.py.

Job logic:
  1. Query loans with due_date within reminder_days_before days that have NOT been
     reminded yet (reminder_sent_at IS NULL) — send due-date reminder email.
  2. Query overdue loans (returned_at IS NULL, due_date < now) that have NOT been
     alerted yet (overdue_sent_at IS NULL) — send overdue alert email.
  3. Set sent_at flags before committing to prevent duplicate sends on subsequent
     scheduler runs (T-04-08 mitigated).

Email functions log to stdout in dev; replace with SMTP calls for production.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import async_session_maker
from app.models.copy import Copy
from app.models.library_settings import LibrarySettings
from app.models.loan import Loan
from app.services.email_service import send_due_date_reminder, send_overdue_alert

logger = logging.getLogger(__name__)


async def run_notification_job() -> None:
    """
    Find loans needing notification emails and send them.

    Runs once at startup and then on a daily interval (configured in scheduler.py).
    """
    try:
        async with async_session_maker() as session:
            now = datetime.now(timezone.utc)

            # Load reminder_days_before from library_settings (default 1 if no row)
            settings_result = await session.execute(
                select(LibrarySettings).where(LibrarySettings.id == 1)
            )
            library_settings = settings_result.scalar_one_or_none()
            reminder_days_before = (
                library_settings.reminder_days_before if library_settings else 1
            )

            reminder_cutoff = now + timedelta(days=reminder_days_before)

            # ---------- Due-date reminder candidates ----------
            # Loans NOT returned, NOT yet reminded, due within reminder_days_before days
            reminder_result = await session.execute(
                select(Loan)
                .options(
                    selectinload(Loan.borrower),
                    selectinload(Loan.copy).selectinload(Copy.book),
                )
                .where(
                    Loan.returned_at.is_(None),
                    Loan.reminder_sent_at.is_(None),
                    Loan.due_date >= now,
                    Loan.due_date <= reminder_cutoff,
                )
            )
            reminder_loans = reminder_result.scalars().all()

            for loan in reminder_loans:
                await send_due_date_reminder(
                    email=loan.borrower.email,
                    book_title=loan.copy.book.title,
                    due_date=loan.due_date.strftime("%Y-%m-%d"),
                )
                loan.reminder_sent_at = now

            # ---------- Overdue alert candidates ----------
            # Loans NOT returned, NOT yet alerted, past due date
            overdue_result = await session.execute(
                select(Loan)
                .options(
                    selectinload(Loan.borrower),
                    selectinload(Loan.copy).selectinload(Copy.book),
                )
                .where(
                    Loan.returned_at.is_(None),
                    Loan.overdue_sent_at.is_(None),
                    Loan.due_date < now,
                )
            )
            overdue_loans = overdue_result.scalars().all()

            for loan in overdue_loans:
                await send_overdue_alert(
                    email=loan.borrower.email,
                    book_title=loan.copy.book.title,
                    due_date=loan.due_date.strftime("%Y-%m-%d"),
                )
                loan.overdue_sent_at = now

            await session.commit()

            logger.info(
                "Notification job completed: %d reminder(s), %d overdue alert(s) sent",
                len(reminder_loans),
                len(overdue_loans),
            )

    except Exception:
        logger.exception("Notification job failed")
