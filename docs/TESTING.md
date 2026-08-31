# Testing

## Overview

Testing is done incrementally with every phase. Each endpoint and service has unit and/or integration tests.

## Frameworks

- **Pytest** — backend and core testing
- **FastAPI TestClient** — API endpoint testing
- **psycopg2** — database connectivity via SQLAlchemy

## Running Tests

From the project root:

```bash
# Run all tests
pytest

# Run a specific file
pytest tests/test_system.py

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest --cov=app
```

## Test Database

A single database (`compliance_scanner`) is used for both tests and the running app. For a local prototype, a separate test database is unnecessary — demo/seed data lives in the same database the app reads from.

Connection settings come from environment variables (see `app/core/config.py`). Values are provided via `.env` (gitignored):

```
postgresql://<user>:<url-encoded-password>@localhost:5432/compliance_scanner
```

The `.env` file must be present for tests that touch the database (`test_readiness`, `test_models`). The `test_system.py` non-DB endpoint tests run even without it.

Demo data is populated with:
```bash
python -m scripts.seed_db
```
This creates one user per role, all 17 rules, and sample products/analyses.

## Test Structure

```
tests/
├── conftest.py          # Shared fixtures (TestClient, DB table creation)
├── test_system.py       # Health/version endpoint tests
└── test_models.py       # SQLAlchemy model and DB schema tests
```

### conftest.py

- Sets `DATABASE_URL` to the main database before importing app modules
- Provides `client` fixture — a FastAPI TestClient
- Creates tables if they do not exist (best-effort)

## Current Test Coverage

### API Endpoints (test_system.py)

| Endpoint | Test |
|----------|------|
| GET /health | test_root_health |
| GET /api/v1/health | test_health_check |
| GET /api/v1/health/live | test_liveness |
| GET /api/v1/health/ready | test_readiness |
| GET /api/v1 | test_api_v1_root |
| GET /api/v1/version | test_version_endpoint |
| GET /openapi.json | test_openapi_schema |

### Database Models (test_models.py)

| Concern | Test |
|---------|------|
| All 12 tables registered | test_all_models_registered |
| Tables created in real PostgreSQL | test_tables_created_in_db |
| users table columns | test_user_table_columns |
| analyses foreign keys | test_analysis_fk_to_user |
| rule_results foreign keys | test_rule_result_has_rule_fk |
| Model repr | test_model_repr |

## Test Results (Phase 5)

```
14 passed
```

## Testing Convention

Every service must have unit tests.
Every database model must have relevant tests.
Every endpoint must have:
- success case
- failure cases (401, 403, 404, 422)
- role restriction verification

Do not continue to the next phase if tests fail. Fix the failure first.
