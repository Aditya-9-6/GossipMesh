class Settings:
    PROJECT_NAME: str = "GossipMesh"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    JWT_AUDIENCE: str = "gossipmesh"
    JWT_ISSUER: str = "gossipmesh"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    OIDC_DISCOVERY_URL: str | None = None
    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: str | None = None
    OIDC_REDIRECT_URI: str | None = None


settings = Settings()
