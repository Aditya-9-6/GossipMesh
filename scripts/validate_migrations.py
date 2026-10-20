import os
import sys
import logging
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from gossipmesh.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_migrations():
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)

    url = str(settings.DATABASE_URI)

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
    except Exception as e:
        logger.error(f"Could not connect to database to check migrations: {e}")
        sys.exit(1)

    head_rev = script.get_current_head()

    if current_rev != head_rev:
        logger.error(f"Database is not up-to-date. Current revision: {current_rev}, Head revision: {head_rev}")
        sys.exit(1)

    logger.info(f"Database is up-to-date. Current revision: {current_rev}")
    return True


if __name__ == "__main__":
    validate_migrations()
