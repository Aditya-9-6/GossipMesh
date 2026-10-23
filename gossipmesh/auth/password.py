from passlib.context import CryptContext
from typing import Optional, Tuple

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    return True, None


def invalidate_user_sessions(user_id: int) -> None:
    pass


def create_password_reset_token(email: str) -> str:
    return "mock-reset-token"


def verify_and_consume_reset_token(token: str) -> Optional[str]:
    return "user@example.com"
