from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "gossipmesh"
    JWT_AUDIENCE: str = "gossipmesh"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URI: str = "postgresql://postgres:postgres@localhost:5432/gossipmesh"
    REDIS_URI: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str = "some-fernet-secret-key-32-bytes-long=="

    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""

    OIDC_DISCOVERY_URL: str | None = None
    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: str | None = None
    OIDC_REDIRECT_URI: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
