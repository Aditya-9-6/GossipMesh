from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gossipmesh.core.config import settings

uri = str(settings.DATABASE_URI)

try:
    import psycopg2

    if not hasattr(psycopg2, "paramstyle"):
        psycopg2.paramstyle = "format"
except ImportError:
    pass

engine = create_engine(
    uri,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
