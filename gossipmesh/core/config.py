from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///gossipmesh.db"
    DATABASE_URI: str = "sqlite:///gossipmesh.db"
    REDIS_URL: Optional[str] = None
    REDIS_URI: Optional[str] = None
    SECRET_KEY: str = "test-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "gossipmesh"
    JWT_AUDIENCE: str = "gossipmesh-users"
    ENCRYPTION_KEY: str = "0123456789abcdef0123456789abcdef"
    ERROR_RATE_THRESHOLD: float = 0.5
    KEY_COOLDOWN_SECONDS: int = 60
    MAX_KEY_RETRIES: int = 3
    DEFAULT_INITIAL_CREDITS: int = 1000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
