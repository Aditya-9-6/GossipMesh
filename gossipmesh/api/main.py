from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from gossipmesh.core.config import settings
from gossipmesh.api.deps import get_db
from gossipmesh.api.routers import (
    artifacts,
    auth,
    enterprise,
    jobs,
    organizations,
    providers,
    repositories,
    runtime,
    scim,
    service_accounts,
    sso,
    users,
    vector_search,
    runs,
    approvals,
)
from gossipmesh.middleware.correlation import CorrelationIdMiddleware, get_correlation_id
from gossipmesh.core.logging import setup_logging
from gossipmesh.api.errors import gossipmesh_exception_handler, global_exception_handler
from gossipmesh.core.exceptions import GossipMeshException

setup_logging()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from gossipmesh.database import engine
        from sqlalchemy import text
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logger.info("Database connection validated successfully.")
    except Exception as e:
        logger.error(f"Failed to validate database connection: {e}")

    try:
        from gossipmesh.database import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as session:
            result = session.execute(text("PRAGMA user_version;")).fetchone()
            if result:
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
        content={"error": {"code": "HTTP_ERROR", "message": exc.detail}, "correlation_id": get_correlation_id()},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": str(exc.errors())}, "correlation_id": get_correlation_id()},
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "correlation_id": get_correlation_id()},
    )

app.add_exception_handler(GossipMeshException, gossipmesh_exception_handler) # type: ignore
app.add_exception_handler(Exception, global_exception_handler) # type: ignore

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/test-db")
def test_db(db = Depends(get_db)):
    return {"db_connection": str(db)}

app.include_router(artifacts.router, prefix=f"{settings.API_V1_STR}/artifacts", tags=["artifacts"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(enterprise.router, prefix=f"{settings.API_V1_STR}/enterprise", tags=["enterprise"])
app.include_router(jobs.router, prefix=f"{settings.API_V1_STR}/jobs", tags=["jobs"])
app.include_router(organizations.router, prefix=f"{settings.API_V1_STR}/organizations", tags=["organizations"])
app.include_router(providers.router, prefix=f"{settings.API_V1_STR}/providers", tags=["providers"])
app.include_router(repositories.router, prefix=f"{settings.API_V1_STR}/repositories", tags=["repositories"])
app.include_router(runtime.router, prefix=f"{settings.API_V1_STR}/runtime", tags=["runtime"])
app.include_router(scim.router, prefix=f"{settings.API_V1_STR}/scim", tags=["scim"])
app.include_router(service_accounts.router, prefix=f"{settings.API_V1_STR}/service-accounts", tags=["service-accounts"])
app.include_router(sso.router, prefix=f"{settings.API_V1_STR}/sso", tags=["sso"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(vector_search.router, prefix=f"{settings.API_V1_STR}/vector-search", tags=["vector-search"])
app.include_router(runs.router, prefix=f"{settings.API_V1_STR}")
app.include_router(approvals.router)
