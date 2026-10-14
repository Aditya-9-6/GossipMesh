from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from gossipmesh.core.config import settings
from gossipmesh.api.routers import auth, users, organizations, providers, repositories, runtime, service_accounts, sso
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Migration Policy: Prevent accidental destructive migrations by validating state
    logger.info("Validating database migration state...")
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)

    engine = create_engine(str(settings.DATABASE_URI))
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            head_rev = script.get_current_head()

            if current_rev != head_rev:
                logger.warning(
                    f"Database migration state is not up-to-date. "
                    f"Current: {current_rev}, Head: {head_rev}. "
                    f"Please run migrations manually."
                )
            else:
                logger.info("Database migration state is up-to-date.")
    except Exception as e:
        logger.error(f"Failed to validate migration state: {e}")
        # Not exiting here to allow app to start even if db is temporarily down,
        # but the warning/error is logged per policy.

    yield
    # Cleanup on shutdown can go here if needed
from gossipmesh.api.errors import gossipmesh_exception_handler, global_exception_handler
from gossipmesh.core.exceptions import GossipMeshException

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(organizations.router, prefix=f"{settings.API_V1_STR}/organizations", tags=["organizations"])
app.include_router(providers.router, prefix=f"{settings.API_V1_STR}/providers", tags=["providers"])
app.include_router(repositories.router, prefix=f"{settings.API_V1_STR}/repositories", tags=["repositories"])
app.include_router(runtime.router, prefix=f"{settings.API_V1_STR}/runtime", tags=["runtime"])
app.include_router(service_accounts.router, prefix=f"{settings.API_V1_STR}/service-accounts", tags=["service-accounts"])
app.include_router(sso.router, prefix=f"{settings.API_V1_STR}/sso", tags=["sso"])

app.add_exception_handler(GossipMeshException, gossipmesh_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
