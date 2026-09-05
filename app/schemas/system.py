"""API-level schemas for health/version responses."""

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str


class VersionResponse(BaseModel):
    name: str
    version: str
    docs_url: str
