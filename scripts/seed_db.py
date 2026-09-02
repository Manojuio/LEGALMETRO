"""Database seed script.

Creates dummy users (one per role) and loads compliance rules.
No test analyses or products — users log in and test themselves.

Idempotent — safe to run multiple times.

Usage:
    python -m scripts.seed_db
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.models import Rule, User, UserRole

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "rules.json"

DUMMY_USERS = [
    {"email": "admin@example.com", "full_name": "System Admin", "role": UserRole.ADMIN, "password": "admin123"},
    {"email": "lmo@example.com", "full_name": "Legal Metrology Officer", "role": UserRole.LMO, "password": "lmo123"},
    {"email": "manufacturer@example.com", "full_name": "ABC Foods Ltd", "role": UserRole.MANUFACTURER, "password": "mfr123"},
    {"email": "retailer@example.com", "full_name": "BigMart Retail", "role": UserRole.RETAILER, "password": "retail123"},
    {"email": "consumer@example.com", "full_name": "Consumer User", "role": UserRole.CONSUMER, "password": "consumer123"},
]


def get_or_create_user(db: Session, data: dict) -> User:
    user = db.query(User).filter(User.email == data["email"]).first()
    if not user:
        user = User(
            email=data["email"],
            full_name=data["full_name"],
            hashed_password=hash_password(data["password"]),
            role=data["role"],
            is_active=True,
        )
        db.add(user)
        db.flush()
    return user


def seed_rules(db: Session) -> int:
    with open(RULES_PATH, encoding="utf-8") as f:
        registry = json.load(f)

    count = 0
    for r in registry["rules"]:
        existing = db.get(Rule, r["id"])
        if existing:
            continue
        db.add(Rule(
            id=r["id"],
            rule_number=r["rule_number"],
            title=r["title"],
            category=r["category"],
            source_reference=r.get("source_reference"),
            requirement=r["requirement"],
            input_fields=r.get("input_fields"),
            validation_type=r["validation_type"],
            severity=r["severity"],
            automation_level=r["automation_level"],
            applicable_to=r.get("applicable_to"),
            package_types=r.get("package_types"),
            evidence_required=r.get("evidence_required"),
            limitations=r.get("limitations"),
            is_active=True,
        ))
        count += 1
    return count


def main() -> None:
    from app.core.database import Base

    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        rules_added = seed_rules(db)
        users = {u["role"]: get_or_create_user(db, u) for u in DUMMY_USERS}
        db.commit()
        print(f"Seeded: {rules_added} new rules, {len(users)} users")
        print("Users:")
        for role, user in users.items():
            print(f"  {role.value:<12} {user.email}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
