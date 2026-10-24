from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from gossipmesh.core.config import settings
from gossipmesh.api.routers import (
    auth,
    users,
    organizations,
    providers,
    repositories,
    runtime,
    artifacts,
    enterprise,
    vector_search,
    service_accounts,
    sso,
    scim,
    runs,
    approvals,
)
from gossipmesh.middleware.correlation import CorrelationIdMiddleware, get_correlation_id
from gossipmesh.core.logging import setup_logging
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from gossipmesh.api.errors import gossipmesh_exception_handler, global_exception_handler
from gossipmesh.core.exceptions import GossipMeshException

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os

    if os.getenv("TESTING", "").lower() in ("true", "1") or "sqlite" in str(settings.DATABASE_URL):
        yield
        return

    # Startup Migration Policy: Prevent accidental destructive migrations by validating state
    logger.info("Validating database migration state...")
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)

    engine = create_engine(str(settings.DATABASE_URL))
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

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "correlation_id": get_correlation_id()},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "correlation_id": get_correlation_id()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import logging

    logger = logging.getLogger(__name__)
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "correlation_id": get_correlation_id()},
    )


app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(organizations.router, prefix=f"{settings.API_V1_STR}/organizations", tags=["organizations"])
app.include_router(providers.router, prefix=f"{settings.API_V1_STR}/providers", tags=["providers"])
app.include_router(repositories.router, prefix=f"{settings.API_V1_STR}/repositories", tags=["repositories"])
app.include_router(runtime.router, prefix=f"{settings.API_V1_STR}/runtime", tags=["runtime"])
app.include_router(artifacts.router, prefix=f"{settings.API_V1_STR}/artifacts", tags=["artifacts"])
app.include_router(enterprise.router, prefix=f"{settings.API_V1_STR}/enterprise", tags=["enterprise"])
app.include_router(vector_search.router, prefix=f"{settings.API_V1_STR}/vector_search", tags=["vector_search"])
app.include_router(service_accounts.router, prefix=f"{settings.API_V1_STR}/service-accounts", tags=["service-accounts"])
app.include_router(sso.router, prefix=f"{settings.API_V1_STR}/sso", tags=["sso"])
app.include_router(scim.router, prefix=f"{settings.API_V1_STR}/scim/v2", tags=["scim"])
app.include_router(runs.router, prefix=f"{settings.API_V1_STR}")
app.include_router(approvals.router)

app.add_exception_handler(GossipMeshException, gossipmesh_exception_handler)  # type: ignore
app.add_exception_handler(Exception, global_exception_handler)  # type: ignore


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/metrics")
def prometheus_metrics():
    from fastapi import Response
    from gossipmesh.observability.metrics import CONTENT_TYPE_LATEST, generate_latest_metrics

    return Response(content=generate_latest_metrics(), media_type=CONTENT_TYPE_LATEST)
