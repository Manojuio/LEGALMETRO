"""Database seed script.

Loads test entities into the single compliance_scanner database:
- One sample user per role (ADMIN, LMO, MANUFACTURER, RETAILER, CONSUMER)
- All rules from rules/rules.json
- Sample products
- Sample analyses with OCR/extracted fields/rule results for demo

Idempotent — safe to run multiple times.

Usage:
    python -m scripts.seed_db
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    Analysis,
    AnalysisStatus,
    ExtractedField,
    Product,
    Rule,
    RuleResult,
    RuleStatus,
    User,
    UserRole,
)

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "rules.json"

SAMPLE_USERS = [
    {"email": "admin@example.com", "full_name": "System Admin", "role": UserRole.ADMIN, "password": "admin123"},
    {"email": "lmo@example.com", "full_name": "Legal Metrology Officer", "role": UserRole.LMO, "password": "lmo123"},
    {"email": "manufacturer@example.com", "full_name": "ABC Foods Ltd", "role": UserRole.MANUFACTURER, "password": "mfr123"},
    {"email": "retailer@example.com", "full_name": "BigMart Retail", "role": UserRole.RETAILER, "password": "retail123"},
    {"email": "consumer@example.com", "full_name": "Consumer User", "role": UserRole.CONSUMER, "password": "consumer123"},
]

SAMPLE_PRODUCTS = [
    {
        "name": "Premium Tea",
        "category": "FOOD",
        "subcategory": "FOOD_BEVERAGES",
        "brand": "ABC Foods",
        "description": "500g loose leaf tea in retail pack",
    },
    {
        "name": "Moisturizing Shampoo",
        "category": "COSMETIC",
        "subcategory": "COS_HAIR",
        "brand": "GlowCare",
        "description": "200ml shampoo bottle",
    },
]

ANALYSIS_FIELDS = {
    "generic_name": "Premium Tea",
    "net_quantity": "500 g",
    "mrp": "450",
    "manufacturer": "ABC Foods",
    "packing_date": "08/2026",
    "consumer_care": "consumer-care@abcfoods.com",
}


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


def seed_products_and_analyses(db: Session, manufacturer: User) -> int:
    created = 0
    for p in SAMPLE_PRODUCTS:
        product = db.query(Product).filter(Product.name == p["name"]).first()
        if not product:
            product = Product(
                name=p["name"],
                category=p["category"],
                subcategory=p.get("subcategory"),
                brand=p.get("brand"),
                description=p.get("description"),
                created_by=manufacturer.id,
            )
            db.add(product)
            db.flush()

        # Skip if an analysis already exists for this product (idempotent)
        existing = (
            db.query(Analysis)
            .filter(
                Analysis.product_id == product.id,
                Analysis.user_id == manufacturer.id,
            )
            .first()
        )
        if existing:
            continue

        analysis = Analysis(
            user_id=manufacturer.id,
            product_id=product.id,
            status=AnalysisStatus.COMPLETED,
        )
        db.add(analysis)
        db.flush()

        for fname, fval in ANALYSIS_FIELDS.items():
            db.add(ExtractedField(
                analysis_id=analysis.id,
                field_name=fname,
                field_value=fval,
                field_value_numeric=float(fval) if fval.replace(".", "", 1).isdigit() else None,
                confidence=0.9,
                extraction_method="seed",
            ))

        for rule_id in ["LM-R3-001", "LM-R6-001", "LM-R9-001"]:
            rule = db.get(Rule, rule_id)
            if rule:
                db.add(RuleResult(
                    analysis_id=analysis.id,
                    rule_id=rule_id,
                    status=RuleStatus.PASS,
                    reason="Seed data — declaration present",
                    confidence=0.95,
                    validator_name="seed",
                ))

        created += 1
    return created


def main() -> None:
    from app.core.database import Base

    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        rules_added = seed_rules(db)

        users = {u["role"]: get_or_create_user(db, u) for u in SAMPLE_USERS}
        manufacturer = users[UserRole.MANUFACTURER]

        analyses_added = seed_products_and_analyses(db, manufacturer)

        db.commit()
        print(f"Seeded: {rules_added} new rules, {len(users)} users, {analyses_added} analyses")
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
