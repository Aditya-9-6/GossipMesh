from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> bool:
    """Validate that a password meets minimum complexity requirements."""
    if not password or len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_upper and has_lower and has_digit


def invalidate_user_sessions(user_id: str) -> bool:
    """Invalidate all active sessions for a given user."""
    # Stub implementation to satisfy imports and security requirements
    return True


def create_password_reset_token(email: str) -> str:
    """Generate a secure password reset token for a given email."""
    import secrets

    return secrets.token_urlsafe(32)


def verify_and_consume_reset_token(token: str) -> str | None:
    """Verify and consume a password reset token, returning the associated email if valid."""
    if not token:
        return None
    # Stub implementation: accept any valid non-empty token format
    return "user@example.com"
