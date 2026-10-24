import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh SaaS"
    VERSION: str = "0.2.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    JWT_AUDIENCE: str = "gossipmesh-api"
    JWT_ISSUER: str = "gossipmesh"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str | None = None
    OIDC_DISCOVERY_URL: str | None = None

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
    KEY_COOLDOWN_SECONDS: int = int(os.getenv("KEY_COOLDOWN_SECONDS", "300"))
    MAX_KEY_RETRIES: int = int(os.getenv("MAX_KEY_RETRIES", "3"))
    # Load provider API keys list (optional, can be empty)
    PROVIDER_API_KEYS: list[str] = (
        os.getenv("PROVIDER_API_KEYS", "").split(",") if os.getenv("PROVIDER_API_KEYS") else []
    )

    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: str | None = None
    OIDC_REDIRECT_URI: str | None = None

    @property
    def REDIS_URI(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


settings = Settings()  # type: ignore
DEFAULT_INITIAL_CREDITS = settings.DEFAULT_INITIAL_CREDITS
ERROR_RATE_THRESHOLD = settings.ERROR_RATE_THRESHOLD
KEY_COOLDOWN_SECONDS = settings.KEY_COOLDOWN_SECONDS
MAX_KEY_RETRIES = settings.MAX_KEY_RETRIES


def parse_key_pool(pool_str: str) -> list[str]:
    """Parses a comma-separated key pool string into a list of keys."""
    if not pool_str:
        return []
    return [k.strip() for k in pool_str.split(",") if k.strip()]
