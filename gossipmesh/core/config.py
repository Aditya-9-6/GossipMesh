import os
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic import PostgresDsn, RedisDsn


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh SaaS"
    VERSION: str = "0.2.0"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "gossipmesh"
    JWT_AUDIENCE: str = "gossipmesh-api"

    ENCRYPTION_KEY: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"

    DEFAULT_INITIAL_CREDITS: int = int(os.getenv("DEFAULT_INITIAL_CREDITS", "1000"))
    ERROR_RATE_THRESHOLD: float = float(os.getenv("ERROR_RATE_THRESHOLD", "0.25"))
    # Load provider API keys list (optional, can be empty)
    PROVIDER_API_KEYS: list[str] = os.getenv("PROVIDER_API_KEYS", "").split(",") if os.getenv("PROVIDER_API_KEYS") else []
    GITHUB_CLIENT_SECRET: str | None = None

    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: str | None = None
    OIDC_DISCOVERY_URL: str | None = None
    OIDC_REDIRECT_URI: str | None = None

    @property
    def DATABASE_URI(self) -> PostgresDsn | str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URI(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


settings = Settings()  # type: ignore
