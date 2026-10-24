import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

database_url = os.getenv("DATABASE_URL", "sqlite:///:memory:")
if database_url.startswith("sqlite"):
    engine = create_engine(database_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
else:
    try:
        engine = create_engine(database_url)
    except Exception:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
