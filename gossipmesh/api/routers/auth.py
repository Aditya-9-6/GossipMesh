import os
from datetime import timedelta, datetime, timezone
import uuid
import urllib.parse
from typing import Any
import httpx
import fastapi
from fastapi import APIRouter, Depends, status, Response, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import jwt
from pydantic import ValidationError, EmailStr

from gossipmesh.api import deps
from gossipmesh.core.config import settings
from gossipmesh.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    encrypt_string,
    decrypt_string,
    get_password_hash,
)
from gossipmesh.core.exceptions import AuthenticationError, AuthorizationError
from gossipmesh.models.user import User
from gossipmesh.models.session import UserSession, RefreshToken
from gossipmesh.models.user import UserGitHubCredential
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.audit import AuditEvent
from gossipmesh.db.redis import redis_client
from gossipmesh.auth.password import (
    validate_password_strength,
    invalidate_user_sessions,
    create_password_reset_token,
    verify_and_consume_reset_token,
)
from gossipmesh.auth.throttle import login_throttler
from pydantic import BaseModel
import base64
import hashlib
from gossipmesh.models.user import UserOIDCCredential

router = APIRouter()


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


@router.post("/login/access-token", response_model=Token)
def login_access_token(
    request: Request, db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    is_locked, remaining = login_throttler.check_lockout(form_data.username)
    if is_locked:
        raise HTTPException(
            status_code=429,
            detail=f"Account temporarily locked due to excessive failed login attempts. Please try again in {remaining} seconds.",
        )
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        is_now_locked, remaining, delay = login_throttler.record_failure(form_data.username)
        if delay > 0:
            import time

            time.sleep(delay)
        if is_now_locked:
            raise HTTPException(
                status_code=429,
                detail=f"Account temporarily locked due to excessive failed login attempts. Please try again in {remaining} seconds.",
            )
        raise AuthenticationError(message="Incorrect email or password")
    elif not user.is_active:
        raise AuthorizationError(message="Inactive user")
    login_throttler.record_success(form_data.username)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    session = UserSession(user_id=user.id, ip_address=ip_address, user_agent=user_agent)
    db.add(session)
    db.commit()
    db.refresh(session)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    access_token = create_access_token(user.id, session_id=session.id, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(user.id, session_id=session.id, jti=jti, expires_delta=refresh_token_expires)
    db_refresh_token = RefreshToken(
        session_id=session.id, jti=jti, expires_at=datetime.now(timezone.utc) + refresh_token_expires
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
def get_sessions(current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)) -> Any:
    sessions = db.query(UserSession).filter(UserSession.user_id == current_user.id).all()
    return sessions


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=fastapi.Response)
def revoke_session(
    session_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
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
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(deps.get_db)) -> Any:
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            leeway=timedelta(seconds=10),
        )
        token_type = payload.get("type")
        if token_type != "refresh":
            raise AuthenticationError(message="Invalid token type")
        jti = payload.get("jti")
        user_id = payload.get("sub")
        session_id = payload.get("sid")
        if not jti or not user_id or not session_id:
            raise AuthenticationError(message="Invalid token claims")
    except (jwt.InvalidTokenError, ValidationError):
        raise AuthenticationError(message="Invalid refresh token")
    db_token = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not db_token:
        raise AuthenticationError(message="Refresh token not found")
    if db_token.is_revoked:
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if session:
            session.is_active = False
            for rt in session.refresh_tokens:
                rt.is_revoked = True
            db.commit()
        raise AuthenticationError(message="Token has been revoked, session terminated")
    if db_token.expires_at < datetime.now(timezone.utc):
        raise AuthenticationError(message="Refresh token has expired")
    db_token.is_revoked = True
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session or not session.is_active:
        raise AuthenticationError(message="Session is inactive")
    session.last_active_at = datetime.now(timezone.utc)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_jti = str(uuid.uuid4())
    access_token = create_access_token(user_id, session_id=session.id, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(
        user_id, session_id=session.id, jti=new_jti, expires_delta=refresh_token_expires
    )
    new_db_refresh_token = RefreshToken(
        session_id=session.id, jti=new_jti, expires_at=datetime.now(timezone.utc) + refresh_token_expires
    )
    db.add(new_db_refresh_token)
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/github/login")
def github_login(request: Request) -> Any:
    state = str(uuid.uuid4())
    redis_client.set(f"github_oauth_state:{state}", "pending")
    client_id = getattr(settings, "GITHUB_CLIENT_ID", getattr(settings, "GITHUB_CLIENT_SECRET", ""))
    params = {
        "client_id": client_id,
        "redirect_uri": f"{request.base_url}api/v1/auth/github/callback",
        "scope": "read:user user:email read:org",
        "state": state,
    }
    url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/github/callback")
def github_callback(request: Request, code: str, state: str, db: Session = Depends(deps.get_db)) -> Any:
    redis_key = f"github_oauth_state:{state}"
    if not redis_client.get(redis_key):
        raise AuthenticationError(message="Invalid or expired state parameter")
    redis_client.delete(redis_key)
    client_id = getattr(settings, "GITHUB_CLIENT_ID", getattr(settings, "GITHUB_CLIENT_SECRET", ""))
    client_secret = getattr(settings, "GITHUB_CLIENT_SECRET", "")

    with httpx.Client() as client:
        token_response = client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": f"{request.base_url}api/v1/auth/github/callback",
            },
        )
        token_data = token_response.json()
        if "error" in token_data:
            raise AuthenticationError(message=token_data.get("error_description", "Failed to authenticate with GitHub"))
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        user_response = client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        user_response.raise_for_status()
        github_user_data = user_response.json()
        emails_response = client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        emails_response.raise_for_status()
        emails_data = emails_response.json()
        primary_email = next(
            (email["email"] for email in emails_data if email["primary"] and email.get("verified")), None
        )
        if not primary_email:
            raise AuthenticationError(message="No verified primary email found on GitHub account")
        github_user_id = github_user_data["id"]
        user = db.query(User).filter(User.email == primary_email).first()
        if not user:
            user = User(email=primary_email, hashed_password=None, is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        credential = db.query(UserGitHubCredential).filter(UserGitHubCredential.user_id == user.id).first()
        enc_access = encrypt_string(access_token)
        enc_refresh = encrypt_string(refresh_token) if refresh_token else None
        if not credential:
            credential = UserGitHubCredential(
                user_id=user.id,
                github_user_id=github_user_id,
                access_token_ciphertext=enc_access,
                refresh_token_ciphertext=enc_refresh,
                encrypted_access_token=enc_access,
                encrypted_refresh_token=enc_refresh,
            )
            setattr(credential, "encrypted_access_token", enc_access)
            if hasattr(credential, "encrypted_refresh_token"):
                setattr(credential, "encrypted_refresh_token", enc_refresh)
            db.add(credential)
        else:
            credential.github_user_id = github_user_id
            if hasattr(credential, "access_token_ciphertext"):
                credential.access_token_ciphertext = enc_access
            if hasattr(credential, "encrypted_access_token"):
                credential.encrypted_access_token = enc_access
            if refresh_token:
                if hasattr(credential, "refresh_token_ciphertext"):
                    credential.refresh_token_ciphertext = enc_refresh
                if hasattr(credential, "encrypted_refresh_token"):
                    credential.encrypted_refresh_token = enc_refresh

        db.commit()
        orgs_response = client.get(
            "https://api.github.com/user/orgs",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        orgs_response.raise_for_status()
        github_orgs = orgs_response.json()
        org_names = [org["login"] for org in github_orgs]
        installations_response = client.get(
            "https://api.github.com/user/installations",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        installations_count = 0
        if installations_response.status_code == 200:
            installations_count = installations_response.json().get("total_count", 0)
        for org_name in org_names:
            org = db.query(Organization).filter(Organization.name == org_name).first()
            if not org:
                org = Organization(name=org_name)
                db.add(org)
                db.commit()
                db.refresh(org)
            user_org = (
                db.query(UserOrganization)
                .filter(UserOrganization.user_id == user.id, UserOrganization.organization_id == org.id)
                .first()
            )
            if not user_org:
                user_org = UserOrganization(user_id=user.id, organization_id=org.id, role="member")
                db.add(user_org)
        db.commit()
        audit_event = AuditEvent(
            action="github_login",
            actor_id=user.id,
            details={
                "github_id": github_user_id,
                "organizations": org_names,
                "installations_count": installations_count,
            },
        )
        db.add(audit_event)
        db.commit()
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return {
            "access_token": create_access_token(user.id, expires_delta=access_token_expires),
            "token_type": "bearer",
        }


@router.post("/github/refresh-token")
def github_refresh_token(
    current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    credential = db.query(UserGitHubCredential).filter(UserGitHubCredential.user_id == current_user.id).first()
    token_cipher = None
    if credential:
        token_cipher = getattr(
            credential, "access_token_ciphertext", getattr(credential, "encrypted_access_token", None)
        )
    if not credential or not token_cipher:
        raise AuthenticationError(message="No GitHub refresh token available for this user")

    refresh_token = decrypt_string(token_cipher)
    client_id = getattr(settings, "GITHUB_CLIENT_ID", getattr(settings, "GITHUB_CLIENT_SECRET", ""))
    client_secret = getattr(settings, "GITHUB_CLIENT_SECRET", "")

    with httpx.Client() as client:
        token_response = client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        token_data = token_response.json()
        if "error" in token_data:
            raise AuthenticationError(message=token_data.get("error_description", "Failed to refresh GitHub token"))
        new_access_token = token_data["access_token"]
        new_refresh_token = token_data.get("refresh_token")
        if hasattr(credential, "access_token_ciphertext"):
            credential.access_token_ciphertext = encrypt_string(new_access_token)
        if hasattr(credential, "encrypted_access_token"):
            credential.encrypted_access_token = encrypt_string(new_access_token)
        if new_refresh_token:
            if hasattr(credential, "refresh_token_ciphertext"):
                credential.refresh_token_ciphertext = encrypt_string(new_refresh_token)
            if hasattr(credential, "encrypted_refresh_token"):
                credential.encrypted_refresh_token = encrypt_string(new_refresh_token)

        db.commit()
        audit_event = AuditEvent(
            action="github_token_refresh",
            actor_id=current_user.id,
            details={
                "github_id": getattr(credential, "github_user_id", None),
            },
        )
        db.add(audit_event)
        db.commit()
        return {"status": "success", "message": "GitHub token refreshed successfully"}


@router.get("/oidc/login")
def oidc_login(request: Request) -> Any:
    if not settings.OIDC_DISCOVERY_URL or not settings.OIDC_CLIENT_ID or not settings.OIDC_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="OIDC is not configured")
    state = str(uuid.uuid4())
    nonce = str(uuid.uuid4())
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
    )
    redis_client.set(f"oidc_state:{state}", f"{nonce}:{code_verifier}")
    with httpx.Client() as client:
        try:
            discovery_response = client.get(settings.OIDC_DISCOVERY_URL)
            discovery_response.raise_for_status()
            discovery_data = discovery_response.json()
            auth_endpoint = discovery_data.get("authorization_endpoint")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch OIDC discovery document: {e}")
    params = {
        "client_id": settings.OIDC_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "scope": "openid profile email",
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    url = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/oidc/callback")
def oidc_callback(request: Request, state: str, code: str, db: Session = Depends(deps.get_db)) -> Any:
    if (
        not settings.OIDC_DISCOVERY_URL
        or not settings.OIDC_CLIENT_ID
        or not settings.OIDC_CLIENT_SECRET
        or not settings.OIDC_REDIRECT_URI
    ):
        raise HTTPException(status_code=500, detail="OIDC is not configured")
    redis_key = f"oidc_state:{state}"
    state_data = redis_client.get(redis_key)
    if not state_data:
        raise AuthenticationError(message="Invalid or expired state parameter")
    redis_client.delete(redis_key)
    nonce, code_verifier = (
        state_data.decode("utf-8").split(":") if isinstance(state_data, bytes) else state_data.split(":")
    )
    with httpx.Client() as client:
        try:
            discovery_response = client.get(settings.OIDC_DISCOVERY_URL)
            discovery_response.raise_for_status()
            discovery_data = discovery_response.json()
            token_endpoint = discovery_data.get("token_endpoint")
            jwks_uri = discovery_data.get("jwks_uri")
        except Exception as e:
            raise AuthenticationError(message=f"Failed to fetch OIDC discovery document: {e}")
        token_response = client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.OIDC_REDIRECT_URI,
                "client_id": settings.OIDC_CLIENT_ID,
                "client_secret": settings.OIDC_CLIENT_SECRET,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_data = token_response.json()
        if "error" in token_data:
            raise AuthenticationError(message=token_data.get("error_description", "Failed to exchange code"))
        id_token = token_data.get("id_token")
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        if not id_token:
            raise AuthenticationError(message="No id_token received")
        try:
            jwks_client: Any = jwt.PyJWKClient(jwks_uri)
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.OIDC_CLIENT_ID,
                issuer=discovery_data.get("issuer"),
            )
        except Exception as e:
            raise AuthenticationError(message=f"Failed to validate ID token: {e}")
        if claims.get("nonce") != nonce:
            raise AuthenticationError(message="Invalid nonce")
        email = claims.get("email")
        if not email:
            raise AuthenticationError(message="OIDC claims did not contain an email")
        sub = claims.get("sub")
        issuer = claims.get("iss")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, hashed_password=None, is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        credential = (
            db.query(UserOIDCCredential)
            .filter(UserOIDCCredential.user_id == user.id, UserOIDCCredential.issuer == issuer)
            .first()
        )
        if not credential:
            credential = UserOIDCCredential(
                user_id=user.id,
                sub=sub,
                issuer=issuer,
                encrypted_access_token=encrypt_string(access_token),
                encrypted_refresh_token=encrypt_string(refresh_token) if refresh_token else None,
                encrypted_id_token=encrypt_string(id_token),
            )
            db.add(credential)
        else:
            credential.sub = str(sub)
            credential.encrypted_access_token = encrypt_string(access_token)
            if refresh_token:
                credential.encrypted_refresh_token = encrypt_string(refresh_token)
            if id_token:
                credential.encrypted_id_token = encrypt_string(id_token)
        roles = claims.get("groups", claims.get("roles", []))
        if isinstance(roles, list) and roles:
            for role_name in roles:
                org = db.query(Organization).filter(Organization.name == role_name).first()
                if org:
                    user_org = (
                        db.query(UserOrganization)
                        .filter(UserOrganization.user_id == user.id, UserOrganization.organization_id == org.id)
                        .first()
                    )
                    if not user_org:
                        user_org = UserOrganization(user_id=user.id, organization_id=org.id, role="member")
                        db.add(user_org)
        db.commit()
        audit_event = AuditEvent(
            action="oidc_login", actor_id=user.id, details={"sub": sub, "issuer": issuer, "roles_mapped": roles}
        )
        db.add(audit_event)
        db.commit()
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return {
            "access_token": create_access_token(user.id, expires_delta=access_token_expires),
            "token_type": "bearer",
        }


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


@router.post("/password/change")
def change_password(
    body: PasswordChangeRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    if not current_user.hashed_password or not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password.")
    is_valid, err_msg = validate_password_strength(body.new_password, current_user.email)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)
    current_user.hashed_password = get_password_hash(body.new_password)
    invalidate_user_sessions(db, current_user.id)
    event = AuditEvent(
        action="password.changed", actor_id=current_user.id, organization_id=None, details={"user_id": current_user.id}
    )
    db.add(event)
    db.commit()
    return {"message": "Password changed successfully. All previous sessions have been invalidated."}


@router.post("/password/reset-request")
def request_password_reset(
    body: PasswordResetRequest,
    db: Session = Depends(deps.get_db),
) -> Any:
    user = db.query(User).filter(User.email == body.email, User.is_active == True).first()
    if not user:
        return {"message": "If an active account with that email exists, a reset token has been generated."}
    token = create_password_reset_token(db, user)
    event = AuditEvent(
        action="password.reset_requested", actor_id=user.id, organization_id=None, details={"email": user.email}
    )
    db.add(event)
    db.commit()
    return {"message": "Password reset token generated.", "reset_token": token}


@router.post("/password/reset-confirm")
def confirm_password_reset(
    body: PasswordResetConfirm,
    db: Session = Depends(deps.get_db),
) -> Any:
    user = verify_and_consume_reset_token(db, body.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user account.")
    is_valid, err_msg = validate_password_strength(body.new_password, user.email)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)
    user.hashed_password = get_password_hash(body.new_password)
    invalidate_user_sessions(db, user.id)
    event = AuditEvent(
        action="password.reset_completed", actor_id=user.id, organization_id=None, details={"user_id": user.id}
    )
    db.add(event)
    db.commit()
    return {"message": "Password has been reset successfully. All previous sessions have been invalidated."}
