import logging
from contextlib import asynccontextmanager

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from starlette.exceptions import HTTPException as StarletteHTTPException

from gossipmesh.api.errors import global_exception_handler, gossipmesh_exception_handler
from gossipmesh.api.routers import (
    approvals,
    artifacts,
    auth,
    enterprise,
    organizations,
    providers,
    repositories,
    runtime,
    runs,
    scim,
    service_accounts,
    sso,
    users,
    vector_search,
)
from gossipmesh.core.config import settings
from gossipmesh.core.exceptions import GossipMeshException
from gossipmesh.core.logging import setup_logging
from gossipmesh.middleware.correlation import CorrelationIdMiddleware, get_correlation_id

setup_logging()
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


openapi_tags = [
    {
        "name": "auth",
        "description": "Authentication and user authorization via JWT and SCIM tokens. Includes login, registration, and session management.",
    },
    {
        "name": "users",
        "description": "User profile and settings operations.",
    },
    {
        "name": "organizations",
        "description": "Multi-tenant organization management, including roles, invitations, and member access.",
    },
    {
        "name": "providers",
        "description": "AI provider credential management and health checks (e.g. OpenAI, Anthropic, Gemini).",
    },
    {
        "name": "repositories",
        "description": "Repository configurations, webhook endpoints, and version control integrations.",
    },
    {
        "name": "runtime",
        "description": "Runtime APIs including workflow orchestrations and sandboxed executions.",
    },
    {
        "name": "artifacts",
        "description": "Management of generated artifacts and assets.",
    },
    {
        "name": "enterprise",
        "description": "Enterprise specific controls, compliance, and features.",
    },
    {
        "name": "vector_search",
        "description": "Operations relating to vector indexing and retrieval for repository intelligence.",
    },
    {
        "name": "service-accounts",
        "description": "Service account generation, API key management, and related settings.",
    },
    {
        "name": "sso",
        "description": "Single Sign-On adapters and integrations for standard enterprise authentication.",
    },
    {
        "name": "scim",
        "description": "SCIM 2.0 endpoints for user and group provisioning from external identity providers.",
    },
    {
        "name": "runs",
        "description": "Tracking metrics, durations, and details for different automated runs and jobs.",
    },
    {
        "name": "approvals",
        "description": "Approval workflows and review actions.",
    },
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    description="Enterprise API for GossipMesh providing features like tenant isolation, provider health checking, multi-tenant authentication, API rate limiting, and structured errors. See [Documentation](https://github.com/Aditya-9-6/GossipMesh) for more details.",
    openapi_tags=openapi_tags,
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
app.include_router(runs.router, prefix=f"{settings.API_V1_STR}", tags=["runs"])
app.include_router(approvals.router)

app.add_exception_handler(GossipMeshException, gossipmesh_exception_handler)  # type: ignore
app.add_exception_handler(Exception, global_exception_handler)  # type: ignore


@app.get("/health", tags=["system"])
def health_check():
    """
    Check the basic health status of the API service.
    """
    return {"status": "healthy"}
