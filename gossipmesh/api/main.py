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

from gossipmesh.api.deps import get_db
from gossipmesh.api.routers.artifacts import router as artifacts_router
from gossipmesh.api.routers.auth import router as auth_router
from gossipmesh.api.routers.enterprise import router as enterprise_router
from gossipmesh.api.routers.jobs import router as jobs_router
from gossipmesh.api.routers.organizations import router as organizations_router
from gossipmesh.api.routers.providers import router as providers_router
from gossipmesh.api.routers.repositories import router as repositories_router
from gossipmesh.api.routers.runtime import router as runtime_router
from gossipmesh.api.routers.scim import router as scim_router
from gossipmesh.api.routers.service_accounts import router as service_accounts_router
from gossipmesh.api.routers.sso import router as sso_router
from gossipmesh.api.routers.users import router as users_router
from gossipmesh.api.routers.vector_search import router as vector_search_router


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry-run mode for autonomous workflows"
    )
    args = parser.parse_args()

    if args.dry_run:
        print("Dry-run mode activated. Inspecting and analyzing...")
        # Add dry-run specific logic here
        # Generate proposed diff and validate
        print("Dry-run complete.")
        sys.exit(0)

    app = FastAPI(title="GossipMesh API", version="0.1.0")

    # Include routers
    app.include_router(artifacts_router)
    app.include_router(auth_router)
    app.include_router(enterprise_router)
    app.include_router(jobs_router)
    app.include_router(organizations_router)
    app.include_router(providers_router)
    app.include_router(repositories_router)
    app.include_router(runtime_router)
    app.include_router(scim_router)
    app.include_router(service_accounts_router)
    app.include_router(sso_router)
    app.include_router(users_router)
    app.include_router(vector_search_router)

    # Health check endpoint
    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    # Dependency override for testing
    @app.get("/test-db")
    def test_db(db=Depends(get_db)):
        return {"db_connection": str(db)}

    # Start the server
    if __name__ == "__main__":
        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
