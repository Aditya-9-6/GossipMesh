import os
import sys
import json
import argparse
import urllib.request
import urllib.error
import subprocess
import time
import hashlib
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from gossipmesh.core.config import settings
from gossipmesh.api.deps import get_db
from gossipmesh.api.routers import artifacts, auth, enterprise, jobs, organizations, providers, repositories, runtime, scim, service_accounts, sso, users, vector_search
from gossipmesh.middleware.correlation import CorrelationIdMiddleware, get_correlation_id
from gossipmesh.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(CorrelationIdMiddleware)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "correlation_id": get_correlation_id()}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "correlation_id": get_correlation_id()}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    import logging
    logger = logging.getLogger(__name__)
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "correlation_id": get_correlation_id()}
    )

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/test-db")
def test_db(db=Depends(get_db)):
    return {"db_connection": str(db)}

@app.get("/test-db")
def test_db(db=Depends(get_db)):
    return {"db_connection": str(db)}

# Include routers
app.include_router(artifacts.router)
app.include_router(auth.router)
app.include_router(enterprise.router)
app.include_router(jobs.router)
app.include_router(organizations.router)
app.include_router(providers.router)
app.include_router(repositories.router)
app.include_router(runtime.router)
app.include_router(scim.router)
app.include_router(service_accounts.router)
app.include_router(sso.router)
app.include_router(users.router)
app.include_router(vector_search.router)

# Start the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
