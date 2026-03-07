"""
FIE v3 — Environment Configuration
Centralized configuration with validation and defaults.
"""
import os
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("fie_v3.config")


@dataclass(frozen=True)
class Config:
    """Application configuration from environment variables."""

    # Environment
    environment: str = "production"  # dev, staging, production
    debug: bool = False

    # Database
    database_url: str = ""

    # Security
    api_key: str = ""
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"])

    # External APIs
    anthropic_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Monitoring
    sentry_dsn: str = ""

    # Server
    port: int = 8000

    # Backups
    backup_s3_bucket: str = "fie2-backups"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    @property
    def is_staging(self) -> bool:
        return self.environment == "staging"


def load_config() -> Config:
    """Load configuration from environment variables."""
    db_url = os.getenv("DATABASE_URL", os.getenv("FIE_DATABASE_URL", "sqlite:///fie_v3.db"))
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    environment = os.getenv("FIE_ENVIRONMENT", "production")

    cors_raw = os.getenv("CORS_ORIGINS", "")
    cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()] or [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    config = Config(
        environment=environment,
        debug=environment == "dev",
        database_url=db_url,
        api_key=os.getenv("FIE_API_KEY", ""),
        cors_origins=cors_origins,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        sentry_dsn=os.getenv("SENTRY_DSN", ""),
        port=int(os.getenv("PORT", "8000")),
        backup_s3_bucket=os.getenv("BACKUP_S3_BUCKET", "fie2-backups"),
    )

    # Validation warnings
    if config.is_production and not config.api_key:
        logger.warning("Running in production without FIE_API_KEY — API is unprotected")
    if config.is_production and not config.sentry_dsn:
        logger.warning("Running in production without SENTRY_DSN — no error tracking")
    if config.is_production and "sqlite" in config.database_url:
        logger.warning("Running in production with SQLite — use PostgreSQL for production")

    logger.info("Config loaded: environment=%s, db=%s",
                config.environment,
                "postgresql" if "postgresql" in config.database_url else "sqlite")

    return config


# Singleton instance
settings = load_config()
