from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh"
    API_V1_STR: str = "/api/v1"
    DATABASE_URI: str = "sqlite:///gossipmesh.db"
    REDIS_URI: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str = "secret-encryption-key-32bytes-long-min"
    SECRET_KEY: str = "secret-jwt-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "gossipmesh"
    JWT_AUDIENCE: str = "gossipmesh-users"
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    OIDC_DISCOVERY_URL: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_REDIRECT_URI: str = ""


settings = Settings()
