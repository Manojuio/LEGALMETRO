"""Tests for the SQLAlchemy database models.

Verifies that models import correctly, relationships are configured,
and tables can be created in the test database.
"""

from sqlalchemy import inspect

from app.core.database import Base, engine
from app.models import (
    User,
    Product,
    Analysis,
    ProductImage,
    OCRResult,
    ExtractedField,
    Rule,
    RuleResult,
    RuleResultEvidence,
    Inspection,
    Report,
    AuditLog,
)


def test_all_models_registered():
    expected_tables = {
        "users",
        "products",
        "analyses",
        "product_images",
        "ocr_results",
        "extracted_fields",
        "rules",
        "rule_results",
        "rule_result_evidence",
        "inspections",
        "reports",
        "audit_logs",
    }
    registered = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered)


def test_tables_created_in_db():
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    expected = {
        "users",
        "products",
        "analyses",
        "product_images",
        "ocr_results",
        "extracted_fields",
        "rules",
        "rule_results",
        "rule_result_evidence",
        "inspections",
        "reports",
        "audit_logs",
    }
    assert expected.issubset(tables)


def test_user_table_columns():
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("users")}
    assert "id" in cols
    assert "email" in cols
    assert "hashed_password" in cols
    assert "role" in cols
    assert "is_active" in cols


def test_analysis_fk_to_user():
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("analyses")
    fk_cols = {tuple(sorted(fk.get("constrained_columns", []))) for fk in fks}
    assert ("user_id",) in fk_cols
    assert ("product_id",) in fk_cols


def test_rule_result_has_rule_fk():
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("rule_results")
    cols = {tuple(sorted(fk.get("constrained_columns", []))) for fk in fks}
    assert ("analysis_id",) in cols
    assert ("rule_id",) in cols


def test_model_repr():
    assert "User" in repr(User(email="a@b.c", hashed_password="x", full_name="A", role="ADMIN"))
