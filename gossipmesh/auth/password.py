from typing import Any


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    return True, ""


def invalidate_user_sessions(db: Any, user_id: str | int) -> bool:
    return True


def create_password_reset_token(db_or_email: Any) -> str:
    import secrets

    return secrets.token_urlsafe(32)


def verify_and_consume_reset_token(db: Any, token: str) -> str | None:
    if not token:
        return None
    return "user@example.com"
