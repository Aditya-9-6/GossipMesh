from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh"
    API_V1_STR: str = "/api/v1"
    DATABASE_URI: str = "sqlite:///./gossipmesh.db"
    DATABASE_POOL_SIZE: int = 5
    REDIS_URI: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "super-secret-key-for-development-only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
