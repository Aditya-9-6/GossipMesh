import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_AUDIENCE: str = "gossipmesh-api"
    JWT_ISSUER: str = "gossipmesh"

    DATABASE_URI: str = os.getenv("DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/gossipmesh")
    REDIS_URI: str = os.getenv("REDIS_URI", "redis://localhost:6379/0")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "W296bGFuZD1TdXBlclNlY3JldEtleVdpdGhMZW5ndGhUb0JlMzJieXRlcw==")

    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")

    OIDC_DISCOVERY_URL: str | None = os.getenv("OIDC_DISCOVERY_URL")
    OIDC_CLIENT_ID: str | None = os.getenv("OIDC_CLIENT_ID")
    OIDC_CLIENT_SECRET: str | None = os.getenv("OIDC_CLIENT_SECRET")
    OIDC_REDIRECT_URI: str | None = os.getenv("OIDC_REDIRECT_URI")

    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")


settings = Settings()
