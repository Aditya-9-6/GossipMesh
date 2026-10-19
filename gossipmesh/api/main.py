from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from gossipmesh.core.config import settings
from gossipmesh.api.routers import auth, users, organizations, providers, repositories, runtime, artifacts, enterprise, vector_search, service_accounts, sso, scim, runs, approvals
from gossipmesh.middleware.correlation import CorrelationIdMiddleware, get_correlation_id
from gossipmesh.core.logging import setup_logging

setup_logging()
from contextlib import asynccontextmanager
import logging
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from gossipmesh.api.errors import gossipmesh_exception_handler, global_exception_handler
from gossipmesh.core.exceptions import GossipMeshException

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Validating database migration state...")
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_rev = context.get_current_revision()
        head_rev = script.get_current_head()
        if current_rev != head_rev:
            logger.warning(f"Database revision {current_rev} does not match head revision {head_rev}.")
        else:
            logger.info("Database migration state is up-to-date.")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)

app.add_exception_handler(GossipMeshException, gossipmesh_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(organizations.router, prefix=f"{settings.API_V1_STR}/organizations", tags=["organizations"])
app.include_router(providers.router, prefix=f"{settings.API_V1_STR}/providers", tags=["providers"])
app.include_router(repositories.router, prefix=f"{settings.API_V1_STR}/repositories", tags=["repositories"])
app.include_router(runtime.router, prefix=f"{settings.API_V1_STR}/runtime", tags=["runtime"])
app.include_router(artifacts.router, prefix=f"{settings.API_V1_STR}/artifacts", tags=["artifacts"])
app.include_router(enterprise.router, prefix=f"{settings.API_V1_STR}/enterprise", tags=["enterprise"])
app.include_router(vector_search.router, prefix=f"{settings.API_V1_STR}/vector-search", tags=["vector-search"])
app.include_router(service_accounts.router, prefix=f"{settings.API_V1_STR}/service-accounts", tags=["service-accounts"])
app.include_router(sso.router, prefix=f"{settings.API_V1_STR}/sso", tags=["sso"])
app.include_router(scim.router, prefix=f"{settings.API_V1_STR}/scim/v2", tags=["scim"])
app.include_router(runs.router, prefix=f"{settings.API_V1_STR}/runs", tags=["runs"])
app.include_router(approvals.router, prefix=f"{settings.API_V1_STR}/approvals", tags=["approvals"])

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": settings.VERSION}
