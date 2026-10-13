from datetime import timedelta
import uuid
import urllib.parse
from typing import Any
import httpx
from fastapi import APIRouter, Depends, status, Response, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from gossipmesh.api import deps
from gossipmesh.core.config import settings
from gossipmesh.core.security import verify_password, create_access_token, encrypt_string, decrypt_string
from gossipmesh.core.exceptions import AuthenticationError, AuthorizationError
from gossipmesh.models.user import User, UserGitHubCredential
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.audit import AuditEvent
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
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise AuthenticationError(message="Incorrect email or password")
    elif not user.is_active:
        raise AuthorizationError(message="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.get("/github/login")
def github_login(request: Request) -> Any:
    state = str(uuid.uuid4())
    # store state in redis for 5 minutes
    redis_client.setex(f"github_oauth_state:{state}", 300, "pending")

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": f"{request.base_url}api/v1/auth/github/callback",
        "scope": "read:user user:email read:org",
        "state": state,
    }
    url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/github/callback")
def github_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(deps.get_db)
) -> Any:
    # Validate state
    redis_key = f"github_oauth_state:{state}"
    if not redis_client.get(redis_key):
        raise AuthenticationError(message="Invalid or expired state parameter")
    redis_client.delete(redis_key)

    # Exchange code for token
    with httpx.Client() as client:
        token_response = client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{request.base_url}api/v1/auth/github/callback",
            },
        )
        token_data = token_response.json()
        if "error" in token_data:
            raise AuthenticationError(message=token_data.get("error_description", "Failed to authenticate with GitHub"))

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")

        # Fetch user profile
        user_response = client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        user_response.raise_for_status()
        github_user_data = user_response.json()

        # Fetch primary email
        emails_response = client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        emails_response.raise_for_status()
        emails_data = emails_response.json()
        primary_email = next((email["email"] for email in emails_data if email["primary"] and email.get("verified")), None)

        if not primary_email:
            raise AuthenticationError(message="No verified primary email found on GitHub account")

        github_id = github_user_data["id"]

        # Match or create user
        user = db.query(User).filter(User.email == primary_email).first()
        if not user:
            user = User(email=primary_email, hashed_password=None, is_active=True)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Update or create credentials
        credential = db.query(UserGitHubCredential).filter(UserGitHubCredential.user_id == user.id).first()
        if not credential:
            credential = UserGitHubCredential(
                user_id=user.id,
                github_id=github_id,
                encrypted_access_token=encrypt_string(access_token),
                encrypted_refresh_token=encrypt_string(refresh_token) if refresh_token else None
            )
            db.add(credential)
        else:
            credential.github_id = github_id
            credential.encrypted_access_token = encrypt_string(access_token)
            if refresh_token:
                credential.encrypted_refresh_token = encrypt_string(refresh_token)

        db.commit()

        # Fetch organizations
        orgs_response = client.get(
            "https://api.github.com/user/orgs",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        orgs_response.raise_for_status()
        github_orgs = orgs_response.json()

        org_names = [org["login"] for org in github_orgs]

        # Fetch installations
        installations_response = client.get(
            "https://api.github.com/user/installations",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        installations_count = 0
        if installations_response.status_code == 200:
            installations_count = installations_response.json().get("total_count", 0)

        # Map organizations
        for org_name in org_names:
            org = db.query(Organization).filter(Organization.name == org_name).first()
            if not org:
                org = Organization(name=org_name)
                db.add(org)
                db.commit()
                db.refresh(org)

            user_org = db.query(UserOrganization).filter(
                UserOrganization.user_id == user.id,
                UserOrganization.organization_id == org.id
            ).first()

            if not user_org:
                user_org = UserOrganization(
                    user_id=user.id,
                    organization_id=org.id,
                    role="member"
                )
                db.add(user_org)

        db.commit()

        # Audit event
        audit_event = AuditEvent(
            action="github_login",
            actor_id=user.id,
            details={
                "github_id": github_id,
                "organizations": org_names,
                "installations_count": installations_count
            }
        )
        db.add(audit_event)
        db.commit()

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return {
            "access_token": create_access_token(
                user.id, expires_delta=access_token_expires
            ),
            "token_type": "bearer",
        }


@router.post("/github/refresh-token")
def github_refresh_token(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    credential = db.query(UserGitHubCredential).filter(UserGitHubCredential.user_id == current_user.id).first()
    if not credential or not credential.encrypted_refresh_token:
        raise AuthenticationError(message="No GitHub refresh token available for this user")

    refresh_token = decrypt_string(credential.encrypted_refresh_token)

    with httpx.Client() as client:
        token_response = client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        token_data = token_response.json()
        if "error" in token_data:
            raise AuthenticationError(message=token_data.get("error_description", "Failed to refresh GitHub token"))

        new_access_token = token_data["access_token"]
        new_refresh_token = token_data.get("refresh_token")

        credential.encrypted_access_token = encrypt_string(new_access_token)
        if new_refresh_token:
            credential.encrypted_refresh_token = encrypt_string(new_refresh_token)

        db.commit()

        # Audit event
        audit_event = AuditEvent(
            action="github_token_refresh",
            actor_id=current_user.id,
            details={
                "github_id": credential.github_id,
            }
        )
        db.add(audit_event)
        db.commit()

        return {"status": "success", "message": "GitHub token refreshed successfully"}
