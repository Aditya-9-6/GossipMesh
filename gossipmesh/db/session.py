from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from gossipmesh.core.config import settings

import os

DATABASE_URL = settings.DATABASE_URI
if isinstance(DATABASE_URL, object) and hasattr(DATABASE_URL, "__str__"):
    DATABASE_URL = str(DATABASE_URL)

# Fallback to psycopg2 or sqlite if psycopg is missing and not explicitly supported
if "postgresql+psycopg://" in DATABASE_URL:
    try:
        import psycopg
    except ImportError:
        DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql+psycopg2://")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
