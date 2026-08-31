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
    """Provide a FastAPI TestClient.

    Health check / version endpoints do not require authentication or
    database access, so this fixture only sets up the app.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    """Ensure tables exist in the single database.

    Best-effort — /health and /version do not need tables.
    Uses the same database as the running app for demo convenience.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    yield
