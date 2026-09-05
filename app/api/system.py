"""System endpoints: health check and version info."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.system import HealthResponse, VersionResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Health check",
)
def health_check() -> HealthResponse:
    """Return application health status.

    Does not touch the database — used by load balancers and tests.
    """
    settings = get_settings()
    return HealthResponse(status="ok", app_name=settings.APP_NAME, version=settings.APP_VERSION)


@router.get(
    "/health/live",
    response_model=HealthResponse,
    tags=["system"],
    summary="Liveness probe",
)
def liveness() -> HealthResponse:
    """Alias liveness probe. The app is alive if this returns."""
    settings = get_settings()
    return HealthResponse(status="alive", app_name=settings.APP_NAME, version=settings.APP_VERSION)


@router.get(
    "/health/ready",
    tags=["system"],
    summary="Readiness probe with database check",
)
def readiness() -> dict:
    """Return service and database readiness.

    Checks that the PostgreSQL connection works. Returns 503 if the
    database is unreachable.
    """
    settings = get_settings()
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover - depends on external DB
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {type(exc).__name__}",
        )
    return {
        "status": "ready",
        "database": "connected",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get(
    "/version",
    response_model=VersionResponse,
    tags=["system"],
    summary="API version",
)
def version() -> VersionResponse:
    """Return API name and version information."""
    settings = get_settings()
    return VersionResponse(
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
    )
