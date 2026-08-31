# API Documentation

This document tracks all API endpoints. Maintained by the AI on every endpoint change.

---

## GET /health

### Purpose

Root-level health check. Alias for `GET /api/v1/health` exposed at the root path.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Output

200:
```json
{
  "status": "ok",
  "app": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0"
}
```

### Errors

None

### Database changes

None

---

## GET /api/v1

### Purpose

Informational root for the API v1 namespace. Lists available endpoints.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Output

200:
```json
{
  "name": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0",
  "endpoints": ["/api/v1/health", "/api/v1/version"]
}
```

### Errors

None

### Database changes

None

---

## GET /api/v1/health

### Purpose

Application health check. Returns status, app name, and version.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Output

200:
```json
{
  "status": "ok",
  "app_name": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0"
}
```

### Errors

None

### Database changes

None

### Tests

- `tests/test_system.py::test_health_check`

---

## GET /api/v1/health/live

### Purpose

Liveness probe. The process is considered alive if this returns 200.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Output

200:
```json
{
  "status": "alive",
  "app_name": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0"
}
```

### Errors

None

### Database changes

None

### Tests

- `tests/test_system.py::test_liveness`

---

## GET /api/v1/health/ready

### Purpose

Readiness probe. Verifies the PostgreSQL connection is reachable.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Processing

1. Open database session
2. Execute `SELECT 1`
3. Close session
4. Return ready status or 503 on failure

### Output

200:
```json
{
  "status": "ready",
  "database": "connected",
  "app": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0"
}
```

### Errors

- 503: Database unavailable

### Database changes

None (read-only connection check)

### Tests

- `tests/test_system.py::test_readiness`

---

## GET /api/v1/version

### Purpose

Returns API name and version information.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Output

200:
```json
{
  "name": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0",
  "docs_url": "/docs"
}
```

### Errors

None

### Database changes

None

### Tests

- `tests/test_system.py::test_version_endpoint`
