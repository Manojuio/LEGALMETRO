"""Add ``overall_status`` column to the ``inspections`` table.

Safe to run multiple times — the column is only added if it does not already
exist.
"""

import sys
from pathlib import Path

# Ensure the project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.core.database import engine


def migrate():
    with engine.begin() as conn:
        # Check whether the column already exists (PostgreSQL)
        result = conn.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.columns "
                "  WHERE table_name = 'inspections' AND column_name = 'overall_status'"
                ")"
            )
        )
        exists = result.scalar()
        if exists:
            print("Column 'overall_status' already exists — skipping.")
            return

        conn.execute(text("ALTER TABLE inspections ADD COLUMN overall_status VARCHAR(20)"))
        print("Added column 'overall_status' to 'inspections' table.")


if __name__ == "__main__":
    migrate()
