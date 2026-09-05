"""Pytest fixtures.

Uses the single main database (compliance_scanner).
The /health and /version endpoints do not touch the database,
so they work even if the DB is unavailable.

Connection settings are read from environment variables (see config.py).
For tests, set DATABASE_* vars in a `.env` file or environment.
"""

from pathlib import Path
from dotenv import load_dotenv

# Load .env if present so the test DB connection matches local dev settings
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


@pytest.fixture(scope="session")
def client():
    """Provide a public FastAPI TestClient (no auth)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_client(client):
    """Authenticated client logged in as a seeded non-admin user.

    Uses the seeded retailer account (retailer@example.com / retail123),
    which can create analyses and upload images. Created on its own
    TestClient so it does not pollute the public `client` fixture.
    """
    with TestClient(app) as c:
        resp = c.post(
            "/api/v1/auth/login",
            json={"email": "retailer@example.com", "password": "retail123"},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c


@pytest.fixture(scope="session")
def client_factory(client):
    """Return a helper to build an authenticated client for a given role.

    Usage:
        admin = client_factory("admin@example.com", "admin123")
    """
    def _make(email, password):
        c = TestClient(app)
        r = c.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        return c

    return _make


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    """Ensure tables exist in the single database."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    yield
