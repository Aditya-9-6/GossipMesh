import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from gossipmesh.core.config import settings

database_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
if database_url.startswith("sqlite"):
    engine = create_engine(database_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
else:
    try:
        engine = create_engine(database_url)
    except Exception:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
