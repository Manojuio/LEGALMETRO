"""FastAPI application entrypoint.

Phase 5+ — FastAPI Foundation with authentication, RBAC, products,
inspections, and analysis endpoints.
Exposes:
- GET /health
- GET /api/v1/health
- GET /api/v1/version
- auth, products, inspections, analysis routers

CORS configured for local React/Vite frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import system, analysis, auth, products, inspections

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Packaged Commodities Compliance Scanner for "
        "Legal Metrology (Packaged Commodities) Rules, 2011."
    ),
    debug=settings.DEBUG,
)

# CORS for local React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 routers
api_v1_router = system.router
analysis_router = analysis.router
auth_router = auth.router
products_router = products.router
inspections_router = inspections.router


@app.get("/health", tags=["system"], summary="Root health check")
def root_health():
    """Alias for compatibility — returns simple JSON."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/api/v1", tags=["system"], summary="API v1 root")
def api_v1_root():
    """Informational root for the API v1 namespace."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": [
            "/api/v1/health",
            "/api/v1/version",
            "/api/v1/auth/login",
            "/api/v1/analyses",
            "/api/v1/products",
            "/api/v1/inspections",
        ],
    }


# Mount system router under /api/v1
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

# Mount analysis router under /api/v1
app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)

# Mount auth router under /api/v1
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)

# Mount products router under /api/v1
app.include_router(products_router, prefix=settings.API_V1_PREFIX)

# Mount inspections router under /api/v1
app.include_router(inspections_router, prefix=settings.API_V1_PREFIX)
