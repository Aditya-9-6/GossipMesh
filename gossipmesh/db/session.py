from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.core.config import settings

engine = create_engine(
    str(settings.DATABASE_URI),
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
