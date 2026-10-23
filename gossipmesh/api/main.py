from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from gossipmesh.core.config import settings
from gossipmesh.middleware.correlation import CorrelationIdMiddleware, get_correlation_id
from gossipmesh.core.logging import setup_logging

setup_logging()
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from gossipmesh.core.config import settings
from gossipmesh.api.routers import (
    auth,
    users,
    organizations,
    projects,
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
    billing,
    health,
)
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    if os.getenv("TESTING", "").lower() in ("true", "1") or "sqlite" in str(settings.DATABASE_URI):
        yield
        return

    # Startup Migration Policy: Prevent accidental destructive migrations by validating state
    logger.info("Validating database migration state...")
    try:
        alembic_cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)

        engine = create_engine(str(settings.DATABASE_URI), connect_args={"connect_timeout": 2})
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
        "name": "projects",
        "description": "Tenant-scoped project hierarchies and access control.",
    },
    {
        "name": "providers",
        "description": "AI provider credential management and health checks (e.g. OpenAI, Anthropic, Gemini).",
    },
    {
        "name": "repositories",
        "description": "Monitored code repositories and scan configuration policies.",
    },
    {
        "name": "runtime",
        "description": "Execution environments, sandboxing, and job dispatch.",
    },
    {
        "name": "artifacts",
        "description": "Inspection, storage, and quarantine of generated patches and analysis artifacts.",
    },
    {
        "name": "enterprise",
        "description": "Enterprise features, license enforcement, and tenant governance.",
    },
    {
        "name": "vector_search",
        "description": "Codebase semantic retrieval, embeddings, and context assembly.",
    },
    {
        "name": "service-accounts",
        "description": "Machine-to-machine authentication tokens and scopes.",
    },
    {
        "name": "sso",
        "description": "Single sign-on integrations via SAML 2.0 and OIDC.",
    },
    {
        "name": "scim",
        "description": "Directory synchronization and SCIM 2.0 identity provisioning.",
    },
    {
        "name": "billing",
        "description": "Stripe subscription management, usage metering, and billing controls.",
    },
    {
        "name": "health",
        "description": "Service health, readiness probes, and Prometheus metrics.",
    },
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Autonomous Code Review and Continuous Advancement Platform API.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
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
app.include_router(projects.router, prefix=f"{settings.API_V1_STR}/projects", tags=["projects"])
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
app.include_router(billing.router, prefix=f"{settings.API_V1_STR}/billing", tags=["billing"])
app.include_router(health.router, prefix="/health", tags=["health"])


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

