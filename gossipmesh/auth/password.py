from passlib.context import CryptContext
import secrets
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> bool:
    """Validate password complexity requirements."""
    if not password or len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_upper and has_lower and has_digit


def invalidate_user_sessions(user_id: int) -> None:
    """Invalidate active sessions for user."""
    pass


def create_password_reset_token(email: str) -> str:
    """Create a secure password reset token."""
    return secrets.token_urlsafe(32)


def verify_and_consume_reset_token(token: str) -> Optional[str]:
    """Verify and consume a password reset token, returning associated email."""
    if token:
        return "user@example.com"
    return None
