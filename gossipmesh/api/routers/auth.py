from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from gossipmesh.api import deps
import jwt
from gossipmesh.core.config import settings
from gossipmesh.core.security import verify_password, create_access_token, dummy_verify, validate_password_strength, get_password_hash
import time
import secrets
import hashlib
from gossipmesh.core.exceptions import AuthenticationError, AuthorizationError
from gossipmesh.models.user import User
from gossipmesh.db.redis import redis_client
from pydantic import BaseModel

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/login/access-token", response_model=Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    # Check progressive lockout
    email = form_data.username
    lockout_key = f"lockout:{email}"
    if redis_client.exists(lockout_key):
        raise AuthenticationError(message="Account temporarily locked out. Try again later.")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        dummy_verify()
        _increment_login_failures(email)
        raise AuthenticationError(message="Incorrect email or password")

    if not verify_password(form_data.password, user.hashed_password):
        _increment_login_failures(email)
        raise AuthenticationError(message="Incorrect email or password")

    if not user.is_active:
        raise AuthorizationError(message="Inactive user")

    # Reset login failures on success
    redis_client.delete(f"login_failures:{email}")
    redis_client.delete(f"lockout:{email}")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

def _increment_login_failures(email: str) -> None:
    fail_key = f"login_failures:{email}"
    failures = redis_client.incr(fail_key)
    redis_client.expire(fail_key, 90000) # 25 hours expiry for failure count

    if failures >= 5:
        # Progressive lockout
        lockout_time = min(300 * (2 ** (failures - 5)), 86400) # Max 24 hours
        redis_client.setex(f"lockout:{email}", lockout_time, "1")


class Msg(BaseModel):
    message: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

@router.post("/logout", response_model=Msg)
def logout(
    current_user: User = Depends(deps.get_current_user),
    token: str = Depends(deps.reusable_oauth2)
) -> Any:
    # Decode token to get jti and exp
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")

        if jti and exp:
            now = int(time.time())
            ttl = max(0, exp - now)
            if ttl > 0:
                redis_client.setex(f"revoked_token:{jti}", ttl, "1")
    except Exception:
        pass # Ignore decode errors here as deps.get_current_user already validated it

    return {"message": "Successfully logged out"}

@router.post("/change-password", response_model=Msg)
def change_password(
    body: ChangePassword,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    if not verify_password(body.old_password, current_user.hashed_password):
        raise AuthenticationError(message="Incorrect password")

    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise AuthenticationError(message=str(e))

    current_user.hashed_password = get_password_hash(body.new_password)
    db.commit()

    # Invalidate all other sessions for this user
    now = time.time()
    redis_client.set(f"sessions_invalidated_before:{current_user.id}", str(now))

    return {"message": "Password updated successfully"}


class PasswordResetRequest(BaseModel):
    email: str

class PasswordReset(BaseModel):
    token: str
    new_password: str

@router.post("/password-reset-request", response_model=Msg)
def password_reset_request(
    body: PasswordResetRequest,
    db: Session = Depends(deps.get_db)
) -> Any:
    user = db.query(User).filter(User.email == body.email).first()
    if user:
        # Generate secure random token
        raw_token = secrets.token_urlsafe(32)
        # Token format: base64_user_id:raw_token
        import base64
        uid_b64 = base64.urlsafe_b64encode(str(user.id).encode()).decode().rstrip('=')
        reset_token = f"{uid_b64}:{raw_token}"

        # Hash raw token for storage
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Store in redis with 15 mins expiry
        redis_client.setex(f"reset_token:{user.id}", 900, token_hash)

        # TODO: Simulate sending email with reset_token

    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/password-reset", response_model=Msg)
def password_reset(
    body: PasswordReset,
    db: Session = Depends(deps.get_db)
) -> Any:
    import base64
    try:
        uid_b64, raw_token = body.token.split(":")
        # Re-pad base64
        padding = 4 - (len(uid_b64) % 4)
        if padding != 4:
            uid_b64 += "=" * padding
        user_id = int(base64.urlsafe_b64decode(uid_b64).decode())
    except Exception:
        raise AuthenticationError(message="Invalid token")

    stored_hash = redis_client.get(f"reset_token:{user_id}")
    if not stored_hash:
        raise AuthenticationError(message="Invalid or expired token")

    # Hash the provided token and compare
    provided_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    if not secrets.compare_digest(provided_hash, stored_hash if isinstance(stored_hash, str) else stored_hash.decode('utf-8')):
        raise AuthenticationError(message="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthenticationError(message="User not found")

    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise AuthenticationError(message=str(e))

    user.hashed_password = get_password_hash(body.new_password)
    db.commit()

    # Invalidate all sessions
    now = time.time()
    redis_client.set(f"sessions_invalidated_before:{user.id}", str(now))

    # Remove used token
    redis_client.delete(f"reset_token:{user_id}")

    return {"message": "Password reset successful"}
