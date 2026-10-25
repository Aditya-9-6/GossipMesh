import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from gossipmesh.models.organization import Organization, GithubAppInstallation

Base = declarative_base()
engine = create_engine("sqlite:///:memory:")


def test_runs_dummy():
    assert True
