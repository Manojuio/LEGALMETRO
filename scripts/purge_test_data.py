"""Purge all test data while keeping the demo login users.

Keeps:
    - demo seed users (admin/lmo/manufacturer/retailer/consumer@example.com)
    - the rules registry (core compliance rules the engine needs)

Removes (DB):
    - rule_result_evidence, ocr_results, extracted_fields, product_images,
      rule_results, reports, inspections, audit_logs, analyses, products
    - every user EXCEPT the demo seed users

Schema (zone concept removed):
    - drops the legacy `zones` table and the `users.zone_id` column, if present

Removes (filesystem):
    - uploaded analysis images (uploads/)
    - generated report PDFs (reports/)

Usage:
    python scripts/purge_test_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.core.database import SessionLocal, engine

# The only users we keep — the demo seed logins.
DEMO_EMAILS = {
    "admin@example.com",
    "lmo@example.com",
    "manufacturer@example.com",
    "retailer@example.com",
    "consumer@example.com",
}

# Child -> parent delete order.
ANALYTICS_TABLES = [
    "rule_result_evidence",
    "extracted_fields",
    "ocr_results",
    "product_images",
    "rule_results",
    "reports",
    "inspections",
    "audit_logs",
    "analyses",
    "products",
]


def purge_filesystem() -> None:
    root = Path(__file__).resolve().parent.parent
    for sub in ("uploads", "reports"):
        target = root / sub
        if not target.exists():
            print(f"  Skipped (missing): {target}")
            continue
        deleted = 0
        if sub == "uploads":
            for child in target.iterdir():
                if child.is_dir():
                    for f in list(child.rglob("*")):
                        if f.is_file():
                            f.unlink(missing_ok=True)
                            deleted += 1
                    child.rmdir()
                elif child.is_file():
                    child.unlink(missing_ok=True)
                    deleted += 1
        else:  # reports
            for f in list(target.glob("*.pdf")):
                f.unlink(missing_ok=True)
                deleted += 1
        print(f"  Cleared {target} ({deleted} files)")


def drop_legacy_zone_schema() -> None:
    """Remove the (now-removed) zone concept from an existing database.

    The zone model was removed; this drops the legacy `zones` table and the
    `users.zone_id` column so the live DB matches the current models. Safe to
    run on databases that never had zones (statements are guarded).
    """
    insp = __import__("sqlalchemy", fromlist=["inspect"]).inspect(engine)
    tables = insp.get_table_names()

    with engine.begin() as conn:
        if "users" in tables and "zone_id" in [c["name"] for c in insp.get_columns("users")]:
            conn.execute(text("ALTER TABLE users DROP COLUMN zone_id"))
            print("  Dropped column: users.zone_id")

    if "zones" in tables:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE zones"))
            print("  Dropped table: zones")
    else:
        print("  No legacy zones table present")


def main() -> None:
    db = SessionLocal()
    try:
        # 1. Analytics / test rows (child-first ordering).
        with engine.begin() as conn:
            for table in ANALYTICS_TABLES:
                conn.execute(text(f"DELETE FROM {table}"))
                print(f"  Cleared rows: {table}")

        # 2. Remove every user except the demo seed users.
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM users WHERE email NOT IN :emails"),
                {"emails": tuple(DEMO_EMAILS)},
            )
            print(f"  Kept users: {', '.join(sorted(DEMO_EMAILS))}")

        print("\nTest data purged. Rules & demo users preserved.")
    finally:
        db.close()


if __name__ == "__main__":
    purge_filesystem()
    main()
    drop_legacy_zone_schema()
