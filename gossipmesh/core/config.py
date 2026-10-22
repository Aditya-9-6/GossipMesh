from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh"
    API_V1_STR: str = "/api/v1"
    DATABASE_URI: str = "sqlite:///./gossipmesh.db"
    REDIS_URI: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    JWT_AUDIENCE: str = "gossipmesh-auth"
    JWT_ISSUER: str = "gossipmesh"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
