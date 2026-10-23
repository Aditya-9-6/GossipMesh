from passlib.context import CryptContext
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> bool:
    if not password or len(password) < 8:
        return False
    return True


def invalidate_user_sessions(user_id: int) -> None:
    pass


def create_password_reset_token(email: str) -> str:
    return f"reset-token-{email}"


def verify_and_consume_reset_token(token: str) -> Optional[str]:
    if token.startswith("reset-token-"):
        return token.replace("reset-token-", "")
    return None
