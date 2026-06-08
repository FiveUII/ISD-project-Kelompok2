"""
Email service — v1 dev implementation.

Real SMTP delivery is Phase 4. For now, the verification URL is logged to stdout
so the flow is fully testable end-to-end without an actual mail server.

Design: async function signature so callers can await it; easy to swap for a real
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

    # Log at INFO so the link is visible in dev server output
    logger.info(
        "EMAIL VERIFICATION LINK (dev — not sent via SMTP):\n"
        "  To: %s\n"
        "  Link: %s",
        email,
        verification_url,
    )
