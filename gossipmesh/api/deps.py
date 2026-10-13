from typing import Generator
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

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token"
)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = payload.get("sub")
        jti = payload.get("jti")
        iat = payload.get("iat")

        if token_data is None:
            raise AuthenticationError(message="Could not validate credentials")

        # Check token blocklist
        if jti and redis_client.exists(f"revoked_token:{jti}"):
            raise AuthenticationError(message="Token has been revoked")

        # Check session invalidation (password change)
        if iat:
            invalidated_before = redis_client.get(f"sessions_invalidated_before:{token_data}")
            if invalidated_before and float(iat) < float(invalidated_before):
                raise AuthenticationError(message="Session has been invalidated")

    except (jwt.InvalidTokenError, ValidationError):
        raise AuthenticationError(message="Could not validate credentials")

    user = db.query(User).filter(User.id == token_data).first()
    if not user:
        raise AuthenticationError(message="User not found")
    if not user.is_active:
        raise AuthorizationError(message="Inactive user")
    return user
