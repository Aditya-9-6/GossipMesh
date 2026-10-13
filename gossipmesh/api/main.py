from fastapi import FastAPI

from gossipmesh.api.routers import (
    auth,
    organizations,
    providers,
    repositories,
    runtime,
    users,
)
from gossipmesh.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(organizations.router, prefix=f"{settings.API_V1_STR}/organizations", tags=["organizations"])
app.include_router(providers.router, prefix=f"{settings.API_V1_STR}/providers", tags=["providers"])
app.include_router(repositories.router, prefix=f"{settings.API_V1_STR}/repositories", tags=["repositories"])
app.include_router(runtime.router, prefix=f"{settings.API_V1_STR}/runtime", tags=["runtime"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}
