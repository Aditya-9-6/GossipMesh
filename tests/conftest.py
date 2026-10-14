import os
import pytest
from fastapi.testclient import TestClient

# Set up required environment variables before any tests run
os.environ["ENCRYPTION_KEY"] = "b_wH5yL7g3XQz8T1kVcZp6sN0mR9dE2fA4uYxWqVjMw="
os.environ["SECRET_KEY"] = "supersecretkey_please_change_in_production"
os.environ["POSTGRES_USER"] = "testuser"
os.environ["POSTGRES_PASSWORD"] = "testpass"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "testdb"

from gossipmesh.api.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_env():
    """Ensure environment variables are set for all tests."""
    pass

@pytest.fixture
def test_client():
    """Provide a FastAPI TestClient."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def mock_db_session():
    """Provide a real in-memory sqlite session instead of MagicMock."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from gossipmesh.models.base import Base

    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
