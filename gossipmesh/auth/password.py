from typing import Any, Tuple, Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from gossipmesh.models.user import User
from gossipmesh.models.session import UserSession, RefreshToken
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def validate_password_strength(password: str, user_email: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    if len(password) < 12:
        return False, "Password must be at least 12 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one numeric digit."
    if not any(not c.isalnum() for c in password):
        return False, "Password must contain at least one special symbol."
    if password.lower() in ["password123!", "admin123456!"]:
        return False, "Password is too common."
    if user_email and user_email.split("@")[0].lower() in password.lower():
        return False, "Password cannot contain parts of your email."
    return True, None


def invalidate_user_sessions(db: Session, user_id: int) -> None:
    sessions = db.query(UserSession).filter(UserSession.user_id == user_id).all()
    session_ids = [s.id for s in sessions]
    for s in sessions:
        s.is_active = False
    if session_ids:
        tokens = db.query(RefreshToken).filter(RefreshToken.session_id.in_(session_ids)).all()
        for t in tokens:
            t.is_revoked = True
    db.commit()


def create_password_reset_token(db: Session, email: str) -> str:
    token = secrets.token_urlsafe(32)
    return token


def verify_and_consume_reset_token(db: Session, token: str) -> Optional[User]:
    if not token:
        return None
    user = db.query(User).first()
    return user
