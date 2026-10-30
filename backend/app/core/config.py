"""SentinelHealth core configuration."""

from __future__ import annotations

from typing import List
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables with SENTINEL_ prefix."""

    model_config = SettingsConfigDict(
        env_prefix="SENTINEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Environment & Runtime Mode ──────────────────────────────────────
    # Deployment environment: 'local', 'staging', 'production'
    ENVIRONMENT: str = "production"

    # DEMO_MODE enables rapid local mock token bypass.
    # CRITICAL: Must default to False. Non-local deployments MUST NOT start with DEMO_MODE=True.
    DEMO_MODE: bool = False

    # ── Database ────────────────────────────────────────────────────────
    # Runtime connection (sentinel_app, NOBYPASSRLS)
    DATABASE_URL: str = "postgresql+asyncpg://sentinel_app:sentinel_app_pass_2024@localhost:5432/sentinelhealth"

    # Migration connection (sentinel_migrator, DDL schema owner)
    MIGRATION_DATABASE_URL: str = "postgresql+asyncpg://sentinel_migrator:sentinel_migrator_pass_2024@localhost:5432/sentinelhealth"

    # ── Redis / Celery ──────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Keycloak OIDC ───────────────────────────────────────────────────
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "sentinel"
    KEYCLOAK_CLIENT_ID: str = "sentinel-api"
    KEYCLOAK_AUDIENCE: str = "sentinel-api"

    # ── CORS ────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"])

    # ── Security ────────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-A-REAL-SECRET"

    # ── Timezone ────────────────────────────────────────────────────────
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # ── Privacy suppression ─────────────────────────────────────────────
    # Illustrative demo rules: Anonymisation depends on context and linkability, not universal constants.
    PRIVACY_MIN_CONTRIBUTORS: int = 10
    PRIVACY_SUPPRESS_RANGE_MIN: int = 1
    PRIVACY_SUPPRESS_RANGE_MAX: int = 4

    # ── Runtime Logging ─────────────────────────────────────────────────
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    @model_validator(mode="after")
    def validate_environment_and_demo(self) -> Settings:
        """Enforces that demo authentication cannot be enabled in non-local environments."""
        if self.DEMO_MODE and self.ENVIRONMENT != "local":
            raise ValueError(
                f"Security violation: DEMO_MODE=True is strictly prohibited in '{self.ENVIRONMENT}' environment. "
                "DEMO_MODE may only be enabled when ENVIRONMENT='local'."
            )
        return self

    # ── Derived helpers ─────────────────────────────────────────────────
    @property
    def keycloak_issuer(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}"

    @property
    def keycloak_jwks_uri(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/certs"

    @property
    def keycloak_openid_config_url(self) -> str:
        return f"{self.keycloak_issuer}/.well-known/openid-configuration"


settings = Settings()
