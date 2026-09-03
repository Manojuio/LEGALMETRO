"""Clear all analysis data from the database.

Run this script to reset the database to a clean state:
    python scripts/clear_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from sqlalchemy import create_engine, text

def main():
    settings = get_settings()
    engine = create_engine(settings.database_url)

    tables = [
        "rule_results",
        "extracted_fields",
        "ocr_results",
        "product_images",
        "inspections",
        "analyses",
        "products",
    ]

    with engine.connect() as conn:
        for table in tables:
            try:
                conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                print(f"  Cleared: {table}")
            except Exception as e:
                print(f"  Skipped {table}: {e}")
        conn.commit()

    print("\nDatabase cleared successfully.")

if __name__ == "__main__":
    main()
