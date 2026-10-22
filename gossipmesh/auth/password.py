"""Password security policies, strength validation, and secure reset helpers (Task 41)."""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from gossipmesh.core.security import get_password_hash
from gossipmesh.models.user import User
from gossipmesh.models.session import UserSession, RefreshToken, PasswordResetToken

COMMON_WEAK_PASSWORDS = {
    "password123!",
    "admin123456!",
    "welcome1234!",
    "qwerty12345!",
    "letmein1234!",
    "gossipmesh123!",
    "changeme1234!",
    "password@123",
    "p@ssw0rd123!",
}


def validate_password_strength(password: str, user_email: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Validates password against enterprise complexity policy:
    - Minimum length: 12 characters
    - At least one uppercase letter [A-Z]
    - At least one lowercase letter [a-z]
    - At least one numeric digit [0-9]
    - At least one special symbol [!@#$%^&*()_+-=[]{}|;:,.<>?]
    - Not in common weak/compromised passwords list
    - Does not contain user's email local-part
    """
    if not password or len(password) < 12:
        return False, "Password must be at least 12 characters long."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."

    if not re.search(r"\d", password):
        return False, "Password must contain at least one numeric digit."

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        return False, "Password must contain at least one special symbol."

    if password.lower() in COMMON_WEAK_PASSWORDS:
        return False, "Password is too common and easily guessable."

    if user_email and "@" in user_email:
        local_part = user_email.split("@")[0].lower()
        if len(local_part) >= 3 and local_part in password.lower():
            return False, "Password cannot contain parts of your email address."

    return True, None


def invalidate_user_sessions(db: Session, user_id: int, keep_session_id: Optional[int] = None):
    """Invalidates all active sessions and revokes refresh tokens for a user (session invalidation on password change/reset)."""
    query = db.query(UserSession).filter(UserSession.user_id == user_id, UserSession.is_active == True)
    if keep_session_id is not None:
        query = query.filter(UserSession.id != keep_session_id)

    target_sessions = query.all()
    session_ids = [s.id for s in target_sessions]

    if session_ids:
        db.query(RefreshToken).filter(RefreshToken.session_id.in_(session_ids)).update(
            {"is_revoked": True}, synchronize_session=False
        )
        for sess in target_sessions:
            sess.is_active = False


def create_password_reset_token(db: Session, user: User, expires_minutes: int = 15) -> str:
    """Generates a cryptographically secure, single-use password reset token."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)

    # Invalidate any pending reset tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id, PasswordResetToken.used_at == None
    ).update({"used_at": datetime.now(timezone.utc)}, synchronize_session=False)

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(reset_record)
    db.commit()
    return raw_token


def verify_and_consume_reset_token(db: Session, raw_token: str) -> Optional[User]:
    """Verifies raw token against stored hash, ensuring it is unexpired and unused, and marks it consumed."""
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    token_record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash, PasswordResetToken.used_at == None)
        .first()
    )

    if not token_record:
        return None

    exp = token_record.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if exp < now:
        return None

    token_record.used_at = now
    user = db.query(User).filter(User.id == token_record.user_id, User.is_active == True).first()
    return user
