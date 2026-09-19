"""Application configuration.

All secrets/tuning values come from environment variables (see .env.example).
Nothing sensitive is ever hardcoded or shipped to the frontend.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- app ---
    APP_NAME: str = "VELOOP Rewards Referral API"
    ENV: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # --- database ---
    # postgresql+psycopg://user:pass@host:5432/veloop
    DATABASE_URL: str = "sqlite:///./veloop.db"
    SQL_ECHO: bool = False

    # --- auth ---
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    # --- device / fraud secrets ---
    DEVICE_TOKEN_SECRET: str = "change-me-device-token"
    DEVICE_HASH_SECRET: str = "change-me-device-hash"   # HMAC pepper for device hashing
    IP_HASH_SECRET: str = "change-me-ip-hash"           # HMAC pepper for IP hashing
    DEVICE_TOKEN_EXPIRE_DAYS: int = 180

    # --- ad provider ---
    AD_PROVIDER_SECRET: str = "change-me-ad-provider"   # HMAC for S2S postbacks
    AD_MIN_WATCH_SECONDS: int = 15
    AD_EVENT_MAX_AGE_SECONDS: int = 600

    # --- fraud thresholds (configurable, never exposed) ---
    RISK_REVIEW_THRESHOLD: int = 31
    RISK_HIGH_THRESHOLD: int = 61

    # --- infra ---
    REDIS_URL: str = ""          # optional; in-memory fallback when empty
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,https://veloop-referral-redesign.vercel.app"
    REFERRAL_LINK_BASE: str = "https://www.velooprewards.in/register"

    # --- rate limits (requests / seconds) ---
    RATE_LIMIT_AUTH: str = "10/60"
    RATE_LIMIT_ATTRIBUTE: str = "5/300"
    RATE_LIMIT_AD_EVENT: str = "60/60"
    RATE_LIMIT_READ: str = "120/60"

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Render/Heroku hand out `postgres://...`; SQLAlchemy needs a driver."""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
