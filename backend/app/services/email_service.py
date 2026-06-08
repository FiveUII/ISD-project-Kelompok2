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
