"""
Email service — v1 dev implementation.

Real SMTP delivery is Phase 4. For now, email URLs are logged to stdout
so the flow is fully testable end-to-end without an actual mail server.

Design: async function signatures so callers can await them; easy to swap for a real
SMTP/Resend implementation later without changing the call site.
"""
import logging

logger = logging.getLogger(__name__)

# Default frontend base URL — overridable via FRONTEND_BASE_URL env var
_DEFAULT_FRONTEND_BASE = "http://localhost:5173"


async def send_verification_email(email: str, token: str, frontend_base: str | None = None) -> None:
    """
    Build and log (not yet send) the email verification link.

    Args:
        email: recipient email address
        token: the urlsafe verification token from EmailToken.token
        frontend_base: override for the frontend base URL (useful in tests)
    """
    base = frontend_base or _DEFAULT_FRONTEND_BASE
    verification_url = f"{base}/verify-email?token={token}"

    print(f"EMAIL VERIFICATION LINK (dev): to={email} link={verification_url}")


async def send_password_reset_email(email: str, token: str, frontend_base: str | None = None) -> None:
    """
    Build and log (not yet send) the password reset link.

    Args:
        email: recipient email address
        token: the urlsafe reset token from EmailToken.token
        frontend_base: override for the frontend base URL (useful in tests)

    The reset link format is: {FRONTEND_BASE_URL}/reset-password?token={token}
    Phase 4 will replace this with real SMTP delivery.
    """
    base = frontend_base or _DEFAULT_FRONTEND_BASE
    reset_url = f"{base}/reset-password?token={token}"

    print(f"PASSWORD RESET LINK (dev): to={email} link={reset_url}")


async def send_due_date_reminder(email: str, book_title: str, due_date: str) -> None:
    """
    Log (not yet send via SMTP) a due-date reminder email.

    Args:
        email: borrower's email address
        book_title: title of the checked-out book
        due_date: ISO date string (YYYY-MM-DD)

    Phase 4 dev implementation: logs to stdout/logger.
    Swap for real SMTP delivery by replacing the print/logger calls here.
    """
    msg = f"DUE DATE REMINDER (dev): to={email} book='{book_title}' due={due_date}"
    logger.info(msg)
    print(msg)


async def send_overdue_alert(email: str, book_title: str, due_date: str) -> None:
    """
    Log (not yet send via SMTP) an overdue alert email.

    Args:
        email: borrower's email address
        book_title: title of the overdue book
        due_date: ISO date string (YYYY-MM-DD) of the missed due date

    Phase 4 dev implementation: logs to stdout/logger.
    Swap for real SMTP delivery by replacing the print/logger calls here.
    """
    msg = f"OVERDUE ALERT (dev): to={email} book='{book_title}' due={due_date}"
    logger.info(msg)
    print(msg)
