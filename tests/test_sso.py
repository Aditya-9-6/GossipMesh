import tests # Initialize env vars
import unittest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.sso import OrganizationSAMLConfig
from gossipmesh.core.config import settings

client = TestClient(app)

class TestSSO(unittest.TestCase):
    def setUp(self):
        # We'll use the real in-memory sqlite mock_db_session provided by conftest
        from tests.conftest import mock_db_session as get_mock_db
        # But we need to instantiate it or use the fixture properly.
        # Given this is unittest style, we need to do dependency injection overrides manually.
        pass

    def tearDown(self):
        app.dependency_overrides.clear()

def test_sso_config_and_login(test_client: TestClient):
    # Tests without db thread issues
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from gossipmesh.models.base import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Create an admin user and organization
    user = User(email="admin@example.com", is_active=True)
    db.add(user)
    db.commit()

    org = Organization(name="Acme Corp")
    db.add(org)
    db.commit()

    user_org = UserOrganization(user_id=user.id, organization_id=org.id, role="admin")
    db.add(user_org)
    db.commit()

    app.dependency_overrides[deps.get_current_user] = lambda: user
    app.dependency_overrides[deps.get_db] = lambda: db

    # Test SAML configuration
    cert = "-----BEGIN CERTIFICATE-----\nMIIC...mock...\n-----END CERTIFICATE-----"
    response = test_client.post(
        f"{settings.API_V1_STR}/sso/{org.id}/config",
        json={
            "idp_entity_id": "https://idp.example.com",
            "sso_url": "https://idp.example.com/sso",
            "x509_cert": cert
        }
    )
    assert response.status_code == 200
    assert response.json() == {"message": "SAML configuration saved successfully"}

    # Verify db
    config = db.query(OrganizationSAMLConfig).filter_by(organization_id=org.id).first()
    assert config is not None
    assert config.idp_entity_id == "https://idp.example.com"

    # Test SAML Login initiation (GET)
    response = test_client.get(f"{settings.API_V1_STR}/sso/{org.id}/login", follow_redirects=False)
    assert response.status_code in [302, 303, 307]
    assert "https://idp.example.com/sso" in response.headers["location"]

    # Test SAML ACS endpoint boundary
    response = test_client.post(
        f"{settings.API_V1_STR}/sso/{org.id}/acs",
        data={"SAMLResponse": "PHNhbWxwOlJlc3BvbnNlLi4u"}
    )
    # Our adapter explicitly raises NotImplementedError to keep the boundary secure
    assert response.status_code == 501
    assert "TODO: Full SAML XML validation requires python3-saml" in response.json()["detail"]

    # Test SAML Logout endpoint boundary
    response = test_client.get(f"{settings.API_V1_STR}/sso/{org.id}/logout", follow_redirects=False)
    assert response.status_code == 501
    assert "TODO: Full SAML SLO implementation" in response.json()["detail"]

    app.dependency_overrides.clear()

def test_sso_config_unauthorized(test_client: TestClient):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from gossipmesh.models.base import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Create member user and organization
    user = User(email="member@example.com", is_active=True)
    db.add(user)
    db.commit()

    org = Organization(name="Acme Corp 2")
    db.add(org)
    db.commit()

    user_org = UserOrganization(user_id=user.id, organization_id=org.id, role="member")
    db.add(user_org)
    db.commit()

    app.dependency_overrides[deps.get_current_user] = lambda: user
    app.dependency_overrides[deps.get_db] = lambda: db

    # Test SAML configuration as member (should fail)
    cert = "-----BEGIN CERTIFICATE-----\nMIIC...mock...\n-----END CERTIFICATE-----"
    response = test_client.post(
        f"{settings.API_V1_STR}/sso/{org.id}/config",
        json={
            "idp_entity_id": "https://idp.example.com",
            "sso_url": "https://idp.example.com/sso",
            "x509_cert": cert
        }
    )
    assert response.status_code == 403

    app.dependency_overrides.clear()
