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
        if token_data is None:
            raise AuthenticationError(message="Could not validate credentials")
    except (jwt.InvalidTokenError, ValidationError):
        raise AuthenticationError(message="Could not validate credentials")

    user = db.query(User).filter(User.id == token_data).first()
    if not user:
        raise AuthenticationError(message="User not found")
    return user
