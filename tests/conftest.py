import os
import sys
from unittest.mock import MagicMock

# Global Mocks for missing dependencies in basic CI testing environments
sys.modules["onelogin"] = MagicMock()
sys.modules["onelogin.saml2"] = MagicMock()
sys.modules["onelogin.saml2.auth"] = MagicMock()
sys.modules["stripe"] = MagicMock()
sys.modules["prometheus_client"] = MagicMock()
sys.modules["fastavro"] = MagicMock()


def mock_login(*args, **kwargs):
    return "https://idp.example.com/sso"

def mock_logout(*args, **kwargs):
    return "https://idp.example.com/sls"

mock_auth_instance = MagicMock()
mock_auth_instance.login.side_effect = mock_login
mock_auth_instance.logout.side_effect = mock_logout
mock_auth_class = MagicMock(return_value=mock_auth_instance)
sys.modules["onelogin.saml2.auth"].OneLogin_Saml2_Auth = mock_auth_class

import pytest

# Set up required environment variables before any tests run
os.environ["ENCRYPTION_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
os.environ["SECRET_KEY"] = "supersecretkey_please_change_in_production"
os.environ["POSTGRES_USER"] = "testuser"
os.environ["POSTGRES_PASSWORD"] = "testpass"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "testdb"

@pytest.fixture(scope="session", autouse=True)
def setup_env():
    """Ensure environment variables are set for all tests."""
    pass

@pytest.fixture
def test_client():
    """Provide a FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from gossipmesh.api.main import app

    with TestClient(app) as client:
        yield client

@pytest.fixture
def mock_db_session():
    """Provide a real in-memory sqlite session instead of MagicMock."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from gossipmesh.models.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
