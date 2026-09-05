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
    # Source the full URL from environment or .env.
    # Defaults are only for local development.
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
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # ------------------------------------------------------------------
    # File Storage
    # ------------------------------------------------------------------

    # Local directories are kept for reports/debug/compatibility.
    # Uploaded images will be moved to Cloudinary.
    UPLOAD_DIR: Path = Path("uploads")
    REPORT_DIR: Path = Path("reports")

    # Maximum size of an uploaded image
    MAX_UPLOAD_SIZE_MB: int = 100

    # Allowed image formats
    #
    # image/jpeg covers both:
    #   .jpg
    #   .jpeg
    #
    # image/tiff covers both:
    #   .tif
    #   .tiff
    ALLOWED_IMAGE_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/bmp",
        "image/tiff",
    ]

    # ------------------------------------------------------------------
    # Cloudinary
    # ------------------------------------------------------------------

    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ------------------------------------------------------------------
    # OCR — Core
    # ------------------------------------------------------------------

    OCR_LANGUAGE: list[str] = ["en"]
    OCR_GPU: bool = False
    OCR_MAX_IMAGE_DIM: int = 1000
    OCR_MIN_CONFIDENCE: float = 0.25

    # ------------------------------------------------------------------
    # OCR — Preprocessing
    # ------------------------------------------------------------------

    OCR_DENOISE: bool = True
    OCR_ENABLE_DESKEW: bool = False
    OCR_ENABLE_THRESHOLD: bool = False
    OCR_ENABLE_CLAHE: bool = False

    # ------------------------------------------------------------------
    # OCR — Image Quality
    # ------------------------------------------------------------------

    OCR_MIN_IMAGE_WIDTH: int = 200
    OCR_MIN_IMAGE_HEIGHT: int = 200
    OCR_BLUR_THRESHOLD: float = 100.0
    OCR_BRIGHTNESS_LOW: float = 0.2
    OCR_BRIGHTNESS_HIGH: float = 0.85

    # ------------------------------------------------------------------
    # OCR — Debug
    # ------------------------------------------------------------------

    OCR_ENABLE_DEBUG: bool = False
    OCR_DEBUG_DIR: Path = Path("debug")

    # ------------------------------------------------------------------
    # Pydantic Settings Configuration
    # ------------------------------------------------------------------

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # ------------------------------------------------------------------
    # Database URL
    # ------------------------------------------------------------------

    @property
    def database_url(self) -> str:
        """Build a SQLAlchemy PostgreSQL connection URL.

        The password is URL-encoded so special characters such as
        @, :, /, etc. do not break the connection URL.
        """
        from urllib.parse import quote_plus

        return (
            f"postgresql://{self.DATABASE_USER}:"
            f"{quote_plus(self.DATABASE_PASSWORD)}"
            f"@{self.DATABASE_HOST}:"
            f"{self.DATABASE_PORT}/"
            f"{self.DATABASE_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()