import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-development")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_AUDIENCE: str = "gossipmesh-api"
    JWT_ISSUER: str = "gossipmesh-auth"
    DATABASE_URI: str = os.getenv("DATABASE_URI", "sqlite:///gossipmesh.db")
    REDIS_URI: str = os.getenv("REDIS_URI", "redis://localhost:6379/0")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "0" * 32)
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    OIDC_DISCOVERY_URL: str | None = os.getenv("OIDC_DISCOVERY_URL")
    OIDC_CLIENT_ID: str | None = os.getenv("OIDC_CLIENT_ID")
    OIDC_CLIENT_SECRET: str | None = os.getenv("OIDC_CLIENT_SECRET")
    OIDC_REDIRECT_URI: str | None = os.getenv("OIDC_REDIRECT_URI")
    ERROR_RATE_THRESHOLD: float = 0.5
    KEY_COOLDOWN_SECONDS: int = 60
    MAX_KEY_RETRIES: int = 3
    DEFAULT_INITIAL_CREDITS: int = int(os.getenv("DEFAULT_INITIAL_CREDITS", "1000"))

    def parse_key_pool(self, raw: str) -> list[str]:
        if not raw:
            return []
        return [k.strip() for k in raw.split(",") if k.strip()]


settings = Settings()
