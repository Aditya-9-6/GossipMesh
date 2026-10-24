from typing import Generator, Any
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
from pydantic import ValidationError

from gossipmesh.db.session import SessionLocal
from gossipmesh.core.config import settings
from gossipmesh.models.user import User
from gossipmesh.core.exceptions import AuthenticationError, AuthorizationError
from gossipmesh.db.redis import redis_client

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token")


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


from datetime import timedelta
from gossipmesh.models.session import UserSession


def get_current_user(db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            leeway=timedelta(seconds=10),
        )
        token_type = payload.get("type")
        if token_type != "access":
            raise AuthenticationError(message="Invalid token type")

        user_id = payload.get("sub")
        session_id = payload.get("sid")
        jti = payload.get("jti")
        iat = payload.get("iat")

        if user_id is None:
            raise AuthenticationError(message="Could not validate credentials")

        if session_id:
            session = db.query(UserSession).filter(UserSession.id == session_id).first()
            if not session or not session.is_active:
                raise AuthenticationError(message="Session is inactive")

        if jti and redis_client.exists(f"revoked_token:{jti}"):
            raise AuthenticationError(message="Token has been revoked")

        if iat:
            invalidated_before_val = redis_client.get(f"sessions_invalidated_before:{user_id}")
            if invalidated_before_val:
                invalidated_before = float(
                    invalidated_before_val.decode("utf-8")
                    if isinstance(invalidated_before_val, bytes)
                    else invalidated_before_val
                )
                if float(iat) < invalidated_before:
                    raise AuthenticationError(message="Session has been invalidated")

    except (jwt.InvalidTokenError, ValidationError):
        raise AuthenticationError(message="Could not validate credentials")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthenticationError(message="User not found")
    if not user.is_active:
        raise AuthorizationError(message="Inactive user")
    return user


def get_scim_token(
    authorization: str = Depends(OAuth2PasswordBearer(tokenUrl="token", auto_error=False)),
    db: Session = Depends(get_db),
) -> Any:
    from gossipmesh.models.service_account import APIKey
    from gossipmesh.core.security import verify_password
    from datetime import datetime, timezone

    if not authorization:
        raise AuthenticationError(message="Bearer token required")

    raw_token = authorization
    if raw_token.startswith("Bearer "):
        raw_token = raw_token.split("Bearer ", 1)[1].strip()

    if not raw_token:
        raise AuthenticationError(message="Bearer token required")

    parts = raw_token.split(".", 1)
    if len(parts) == 2:
        prefix, secret = parts
        api_key = db.query(APIKey).filter(APIKey.prefix == prefix, APIKey.is_revoked == False).first()
        if api_key and verify_password(secret, api_key.hashed_key):
            if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
                raise AuthenticationError(message="Token has expired")
            api_key.last_used_at = datetime.now(timezone.utc)
            db.commit()
            return api_key

    api_key = db.query(APIKey).filter(APIKey.prefix == raw_token, APIKey.is_revoked == False).first()
    if api_key:
        return api_key
    raise AuthenticationError(message="Invalid SCIM token")
