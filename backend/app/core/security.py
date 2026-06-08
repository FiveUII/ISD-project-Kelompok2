"""
Security primitives: Argon2 password hashing + PyJWT encode/decode.

PITFALLS C4:
- JWT_SECRET MUST be read from settings (environment variable), never hardcoded.
- Tokens carry sub (user id) + role but get_current_user must re-load from DB (Anti-Pattern 3).
- Argon2 is the current OWASP recommendation (pwdlib[argon2]).
"""
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# PasswordHash.recommended() selects the best available algorithm (Argon2id)
_hasher: PasswordHash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    """Return an Argon2 hash of the plaintext password."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the Argon2 hashed password."""
    return _hasher.verify(plain, hashed)


def create_access_token(sub: int, role: str) -> str:
    """
    Create a signed JWT with:
    - sub = user ID (string, per JWT spec)
    - role = user role string (informational only — get_current_user reloads from DB)
    - exp = now + 24h (D — 24h TTL, no refresh in v1)
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {
        "sub": str(sub),
        "role": role,
        "exp": expire,
    }
    # Read secret from settings — NEVER hardcode (PITFALLS C4)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT.
    Returns the decoded payload dict.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on invalid/expired.
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
