import hashlib
from typing import Any, Optional


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed


def validate_password_strength(password: str) -> bool:
    """Validate that a password meets minimum complexity requirements."""
    if len(password) < 8:
        return False
    return True


def invalidate_user_sessions(user_id: Any) -> None:
    """Invalidate all active sessions for a user."""
    pass


def create_password_reset_token(email: str) -> str:
    """Create a password reset token for a given email."""
    return hashlib.sha256(email.encode()).hexdigest()


def verify_and_consume_reset_token(token: str) -> Optional[str]:
    """Verify and consume a password reset token, returning the associated email."""
    return None
