import os
import re
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn

from gossipmesh.core.safety import safety, SafetyConfig


class Settings(BaseSettings):
    PROJECT_NAME: str = "GossipMesh SaaS"
    VERSION: str = "0.2.0"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = "supersecretkey_please_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "gossipmesh"
    JWT_AUDIENCE: str = "gossipmesh-api"

    ENCRYPTION_KEY: str = "b_wH5yL7g3XQz8T1kVcZp6sN0mR9dE2fA4uYxWqVjMw="

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "gossipmesh"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"

    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None

    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: str | None = None
    OIDC_DISCOVERY_URL: str | None = None
    OIDC_REDIRECT_URI: str | None = None

    @property
    def DATABASE_URI(self) -> PostgresDsn | str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URI(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


def parse_key_pool(raw_val: str | None) -> List[str]:
    """Parses a comma-, pipe-, or newline-separated string into a list of cleaned keys."""
    if not raw_val:
        return []
    keys: List[str] = []
    for chunk in re.split(r"[,\r\n|]+", raw_val):
        cleaned = chunk.strip()
        if cleaned and cleaned not in keys:
            keys.append(cleaned)
    return keys


# Primary Gemini key pools and individual keys
GEMINI_KEY_POOL: List[str] = parse_key_pool(os.getenv("GEMINI_KEY_POOL", ""))
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_ISSUE_KEY: str = os.getenv("GEMINI_ISSUE_KEY", "").strip()
GEMINI_REVIEWER_KEY: str = os.getenv("GEMINI_REVIEWER_KEY", "").strip()
GEMINI_SOLVER_KEY: str = os.getenv("GEMINI_SOLVER_KEY", "").strip()

# Optional multi-provider pools
OPENAI_API_KEYS: List[str] = parse_key_pool(os.getenv("OPENAI_API_KEYS", ""))
GROQ_API_KEYS: List[str] = parse_key_pool(os.getenv("GROQ_API_KEYS", ""))
ANTHROPIC_API_KEYS: List[str] = parse_key_pool(os.getenv("ANTHROPIC_API_KEYS", ""))
DEEPSEEK_API_KEYS: List[str] = parse_key_pool(os.getenv("DEEPSEEK_API_KEYS", ""))

# Operational defaults
DEFAULT_INITIAL_CREDITS: int = int(os.getenv("DEFAULT_INITIAL_CREDITS", "1000"))
ERROR_RATE_THRESHOLD: float = float(os.getenv("ERROR_RATE_THRESHOLD", "0.25"))
KEY_COOLDOWN_SECONDS: int = int(os.getenv("KEY_COOLDOWN_SECONDS", "60"))
MAX_KEY_RETRIES: int = int(os.getenv("MAX_KEY_RETRIES", "5"))

try:
    settings = Settings()
except Exception:
    settings = Settings(_env_file=None)
