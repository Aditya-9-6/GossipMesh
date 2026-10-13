from datetime import timedelta, datetime, timezone
from typing import Any
import uuid
import fastapi
import fastapi
from fastapi import APIRouter, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import jwt
from pydantic import ValidationError

from gossipmesh.api import deps
from gossipmesh.core.config import settings
from gossipmesh.core.security import verify_password, create_access_token, create_refresh_token
from gossipmesh.core.exceptions import AuthenticationError, AuthorizationError
from gossipmesh.models.user import User
from gossipmesh.models.session import UserSession, RefreshToken
from pydantic import BaseModel

router = APIRouter()

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

@router.post("/login/access-token", response_model=Token)
def login_access_token(
    request: Request, db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise AuthenticationError(message="Incorrect email or password")
    elif not user.is_active:
        raise AuthorizationError(message="Inactive user")

    # Create session
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    session = UserSession(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Generate tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    jti = str(uuid.uuid4())
    access_token = create_access_token(user.id, session_id=session.id, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(user.id, session_id=session.id, jti=jti, expires_delta=refresh_token_expires)

    # Store refresh token in db
    db_refresh_token = RefreshToken(
        session_id=session.id,
        jti=jti,
        expires_at=datetime.now(timezone.utc) + refresh_token_expires
    )
    db.add(db_refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

class SessionResponse(BaseModel):
    id: int
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    last_active_at: datetime
    is_active: bool

@router.get("/sessions", response_model=list[SessionResponse])
def get_sessions(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    sessions = db.query(UserSession).filter(UserSession.user_id == current_user.id).all()
    return sessions

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=fastapi.Response)
def revoke_session(
    session_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> None:
    session = db.query(UserSession).filter(UserSession.id == session_id, UserSession.user_id == current_user.id).first()
    if not session:
        raise AuthenticationError(message="Session not found", status_code=status.HTTP_404_NOT_FOUND)

    session.is_active = False
    for rt in session.refresh_tokens:
        rt.is_revoked = True
    db.commit()
    return None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=Token)
def refresh_token(
    request: RefreshTokenRequest, db: Session = Depends(deps.get_db)
) -> Any:
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            leeway=timedelta(seconds=10)
        )
        token_type = payload.get("type")
        if token_type != "refresh":
            raise AuthenticationError(message="Invalid token type")
        jti = payload.get("jti")
        user_id = payload.get("sub")
        session_id = payload.get("sid")
        if not jti or not user_id or not session_id:
            raise AuthenticationError(message="Invalid token claims")
    except (jwt.InvalidTokenError, ValidationError) as e:
        raise AuthenticationError(message="Invalid refresh token")

    db_token = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()

    if not db_token:
        raise AuthenticationError(message="Refresh token not found")

    if db_token.is_revoked:
        # Reuse detection: revoke all tokens for this session
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if session:
            session.is_active = False
            for rt in session.refresh_tokens:
                rt.is_revoked = True
            db.commit()
        raise AuthenticationError(message="Token has been revoked, session terminated")

    if db_token.expires_at < datetime.now(timezone.utc):
        raise AuthenticationError(message="Refresh token has expired")

    # Mark current token as revoked
    db_token.is_revoked = True

    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session or not session.is_active:
        raise AuthenticationError(message="Session is inactive")

    session.last_active_at = datetime.now(timezone.utc)

    # Generate new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_jti = str(uuid.uuid4())
    access_token = create_access_token(user_id, session_id=session.id, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(user_id, session_id=session.id, jti=new_jti, expires_delta=refresh_token_expires)

    # Store new refresh token
    new_db_refresh_token = RefreshToken(
        session_id=session.id,
        jti=new_jti,
        expires_at=datetime.now(timezone.utc) + refresh_token_expires
    )
    db.add(new_db_refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
