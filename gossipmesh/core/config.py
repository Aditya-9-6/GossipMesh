from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh"
    API_V1_STR: str = "/api/v1"
    DATABASE_URI: str = "sqlite:///./gossipmesh.db"
    REDIS_URI: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "supersecretkey"
    ENCRYPTION_KEY: str = "12345678901234567890123456789012"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_AUDIENCE: str = "gossipmesh"
    JWT_ISSUER: str = "gossipmesh-auth"
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    OIDC_DISCOVERY_URL: str | None = None
    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: str | None = None
    OIDC_REDIRECT_URI: str | None = None

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()
