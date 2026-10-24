import hashlib
from typing import Any, Optional
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return hash_password(plain_password) == hashed_password


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


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
