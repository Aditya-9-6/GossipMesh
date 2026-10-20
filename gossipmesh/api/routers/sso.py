from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.sso import OrganizationSAMLConfig
from gossipmesh.models.audit import AuditEvent
from gossipmesh.core.security import encrypt_string, decrypt_string
from gossipmesh.auth.sso.saml_adapter import SAMLAdapter
from gossipmesh.api.routers.organizations import require_org_admin

router = APIRouter()


class SAMLConfigCreate(BaseModel):
    idp_entity_id: str
    sso_url: str
    x509_cert: str


@router.post("/{org_id}/config")
def configure_saml(
    org_id: int,
    config_in: SAMLConfigCreate,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    # Requires organization admin to configure SSO
    require_org_admin(org_id, db, current_user)

    # Validate certificate using the adapter
    adapter = SAMLAdapter(config_in.idp_entity_id, config_in.sso_url, config_in.x509_cert)
    if not adapter.validate_certificate():
        raise HTTPException(status_code=400, detail="Invalid X509 Certificate format")

    encrypted_cert = encrypt_string(config_in.x509_cert)

    config = db.query(OrganizationSAMLConfig).filter(OrganizationSAMLConfig.organization_id == org_id).first()
    if config:
        config.idp_entity_id = config_in.idp_entity_id
        config.sso_url = config_in.sso_url
        config.x509_cert_encrypted = encrypted_cert
    else:
        config = OrganizationSAMLConfig(
            organization_id=org_id,
            idp_entity_id=config_in.idp_entity_id,
            sso_url=config_in.sso_url,
            x509_cert_encrypted=encrypted_cert,
        )
        db.add(config)

    event = AuditEvent(
        action="saml_config.updated",
        actor_id=current_user.id,
        organization_id=org_id,
        details={"idp_entity_id": config_in.idp_entity_id},
    )
    db.add(event)
    db.commit()

    return {"message": "SAML configuration saved successfully"}


@router.get("/{org_id}/login")
def saml_login(org_id: int, db: Session = Depends(deps.get_db)) -> Any:
    config = (
        db.query(OrganizationSAMLConfig)
        .filter(OrganizationSAMLConfig.organization_id == org_id, OrganizationSAMLConfig.is_active)
        .first()
    )

    if not config:
        raise HTTPException(status_code=404, detail="SAML configuration not found or inactive for this organization")

    decrypted_cert = decrypt_string(config.x509_cert_encrypted)
    adapter = SAMLAdapter(config.idp_entity_id, config.sso_url, decrypted_cert)

    redirect_url = adapter.build_authn_request()

    # Using system actor (0) since user is not logged in yet
    event = AuditEvent(action="saml_login.initiated", actor_id=0, organization_id=org_id, details={})
    db.add(event)
    db.commit()

    return RedirectResponse(redirect_url)


@router.post("/{org_id}/acs")
def saml_acs(org_id: int, request: Request, SAMLResponse: str = Form(...), db: Session = Depends(deps.get_db)) -> Any:
    config = (
        db.query(OrganizationSAMLConfig)
        .filter(OrganizationSAMLConfig.organization_id == org_id, OrganizationSAMLConfig.is_active)
        .first()
    )

    if not config:
        raise HTTPException(status_code=404, detail="SAML configuration not found or inactive")

    decrypted_cert = decrypt_string(config.x509_cert_encrypted)
    adapter = SAMLAdapter(config.idp_entity_id, config.sso_url, decrypted_cert)

    try:
        # This will raise NotImplementedError per our secure boundary design
        user_data = adapter.parse_response(SAMLResponse)
    except NotImplementedError as e:
        # Log the attempt and return a 501 Not Implemented gracefully
        event = AuditEvent(
            action="saml_login.failed_not_implemented", actor_id=0, organization_id=org_id, details={"error": str(e)}
        )
        db.add(event)
        db.commit()
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        event = AuditEvent(action="saml_login.failed", actor_id=0, organization_id=org_id, details={"error": str(e)})
        db.add(event)
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid SAML Response")

    # If it was fully implemented, we'd log the user in here and issue a JWT token.
    return {"status": "success", "user": user_data}


@router.get("/{org_id}/logout")
def saml_logout(
    org_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    config = (
        db.query(OrganizationSAMLConfig)
        .filter(OrganizationSAMLConfig.organization_id == org_id, OrganizationSAMLConfig.is_active)
        .first()
    )

    if not config:
        raise HTTPException(status_code=404, detail="SAML configuration not found")

    decrypted_cert = decrypt_string(config.x509_cert_encrypted)
    adapter = SAMLAdapter(config.idp_entity_id, config.sso_url, decrypted_cert)

    try:
        redirect_url = adapter.process_logout()
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))

    event = AuditEvent(action="saml_logout.initiated", actor_id=current_user.id, organization_id=org_id, details={})
    db.add(event)
    db.commit()

    return RedirectResponse(redirect_url)
