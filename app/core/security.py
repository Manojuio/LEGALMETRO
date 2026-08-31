"""Security helpers: password hashing/verification and JWT.

Uses the `bcrypt` library directly (passlib 1.7.4 is incompatible with
bcrypt 4.1+, which errors on passwords near the 72-byte limit). This module
is the single place for password operations and JWT creation/verification,
reused by the authentication API in Phase 6.
"""

import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt

from app.core.config import get_settings


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str, role_claim: str | None = None) -> str:
    """Create a signed JWT access token.

    subject: identifier (user id or "guest" for anonymous scans)
    role: user role name
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
    }
    if role_claim:
        payload["roles"] = [role_claim]
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Raises jose.JWTError on invalid/expired tokens.
    """
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
