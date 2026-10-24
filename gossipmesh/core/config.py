import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn


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
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "0" * 32)
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str | None = os.getenv("GITHUB_CLIENT_SECRET", "")
    OIDC_DISCOVERY_URL: str | None = os.getenv("OIDC_DISCOVERY_URL")
    OIDC_CLIENT_ID: str | None = os.getenv("OIDC_CLIENT_ID")
    OIDC_CLIENT_SECRET: str | None = os.getenv("OIDC_CLIENT_SECRET")
    OIDC_REDIRECT_URI: str | None = os.getenv("OIDC_REDIRECT_URI")
    ERROR_RATE_THRESHOLD: float = float(os.getenv("ERROR_RATE_THRESHOLD", "0.25"))
    KEY_COOLDOWN_SECONDS: int = 60
    MAX_KEY_RETRIES: int = 3
    DEFAULT_INITIAL_CREDITS: int = int(os.getenv("DEFAULT_INITIAL_CREDITS", "1000"))

    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "gossipmesh")

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")

    PROVIDER_API_KEYS: list[str] = (
        os.getenv("PROVIDER_API_KEYS", "").split(",") if os.getenv("PROVIDER_API_KEYS") else []
    )

    def parse_key_pool(self, raw: str) -> list[str]:
        if not raw:
            return []
        return [k.strip() for k in raw.split(",") if k.strip()]

    @property
    def DATABASE_URI(self) -> PostgresDsn | str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URI(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


settings = Settings()  # type: ignore
