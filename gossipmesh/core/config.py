import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic import PostgresDsn, RedisDsn


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///gossipmesh.db"
    REDIS_URL: Optional[str] = None
    SECRET_KEY: str = "test-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "gossipmesh"
    JWT_AUDIENCE: str = "gossipmesh-users"
    ENCRYPTION_KEY: str = "0123456789abcdef0123456789abcdef"
    ERROR_RATE_THRESHOLD: float = float(os.getenv("ERROR_RATE_THRESHOLD", "0.5"))
    KEY_COOLDOWN_SECONDS: int = 60
    MAX_KEY_RETRIES: int = 3
    DEFAULT_INITIAL_CREDITS: int = int(os.getenv("DEFAULT_INITIAL_CREDITS", "1000"))

    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"

    PROVIDER_API_KEYS: list[str] = (
        os.getenv("PROVIDER_API_KEYS", "").split(",") if os.getenv("PROVIDER_API_KEYS") else []
    )
    GITHUB_CLIENT_SECRET: str | None = None

    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: str | None = None
    OIDC_DISCOVERY_URL: str | None = None
    OIDC_REDIRECT_URI: str | None = None

    @property
    def DATABASE_URI(self) -> PostgresDsn | str:
        if self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_HOST and self.POSTGRES_PORT and self.POSTGRES_DB:
            return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self.DATABASE_URL

    @property
    def REDIS_URI(self) -> str:
        if self.REDIS_HOST and self.REDIS_PORT:
            return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return self.REDIS_URL or "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()  # type: ignore
