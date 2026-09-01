"""Application settings loaded from environment variables.

Uses pydantic-settings for type-safe configuration.
Default values are for local development only.
"""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration."""

    # Application
    APP_NAME: str = "Packaged Commodities Compliance Scanner"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Database
    # Source the full URL from environment or .env. Provide a working local
    # defaults only for development; do not hardcode production credentials.
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "compliance_scanner"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = ""

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # File storage
    UPLOAD_DIR: Path = Path("uploads")
    REPORT_DIR: Path = Path("reports")
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # OCR
    OCR_LANGUAGE: list[str] = ["en"]
    OCR_GPU: bool = False
    OCR_MAX_IMAGE_DIM: int = 1800
    OCR_DENOISE: bool = True
    OCR_THRESHOLD: bool = True
    # Blocks below this confidence are kept as evidence but EXCLUDED from the
    # text that feeds extraction — prevents OCR noise masquerading as product
    # data (e.g. logos read as text).
    OCR_MIN_CONFIDENCE: float = 0.25

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def database_url(self) -> str:
        """Build a SQLAlchemy connection URL from components.

        The password is URL-encoded so special characters (@, :, /) do not
        break parsing.
        """
        from urllib.parse import quote_plus

        return (
            f"postgresql://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    """Cached singleton for app settings."""
    return Settings()
