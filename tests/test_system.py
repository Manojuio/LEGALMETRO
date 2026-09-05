"""Tests for Phase 5 — FastAPI Foundation endpoints.

Covers:
- GET /health
- GET /health/live
- GET /api/v1/health
- GET /api/v1/version
- GET /api/v1
"""


def test_root_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"]
    assert data["version"]


def test_health_check(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "Packaged Commodities" in data["app_name"]
    assert data["version"]


def test_liveness(client):
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


def test_readiness(client):
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_api_v1_root(client):
    resp = client.get("/api/v1")
    assert resp.status_code == 200
    data = resp.json()
    assert "endpoints" in data
    assert "/api/v1/health" in data["endpoints"]
    assert "/api/v1/version" in data["endpoints"]


def test_version_endpoint(client):
    resp = client.get("/api/v1/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "docs_url" in data


def test_api_v1_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")


def test_openapi_schema(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/version" in schema["paths"]
