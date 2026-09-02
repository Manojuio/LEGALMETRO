"""Role-based access control tests for auth, zones, products, and inspections.

These verify the rules in docs/ROLES.md using the seeded accounts:
- admin@example.com / admin123
- lmo@example.com / lmo123
- manufacturer@example.com / mfr123
- retailer@example.com / retail123
- consumer@example.com / consumer123
"""

import pytest


# --- Authentication ----------------------------------------------------------


def test_login_admin(client_factory):
    admin = client_factory("admin@example.com", "admin123")
    me = admin.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "ADMIN"


def test_login_wrong_password(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_register_consumer(client):
    import uuid
    email = f"newconsumer{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass123", "full_name": "New User", "role": "CONSUMER"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "CONSUMER"


def test_register_elevated_role_forbidden(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "hacker@example.com", "password": "pass123", "full_name": "H", "role": "LMO"},
    )
    assert r.status_code == 403


# --- Zone management (ADMIN only) --------------------------------------------


def test_zones_admin_only(client_factory):
    # Non-admin cannot list zones
    consumer = client_factory("consumer@example.com", "consumer123")
    assert consumer.get("/api/v1/zones").status_code == 403

    # Admin can create + list zones
    admin = client_factory("admin@example.com", "admin123")
    import uuid
    zone_name = f"Zone-{uuid.uuid4().hex[:6]}"
    r = admin.post("/api/v1/zones", params={"name": zone_name, "jurisdiction": "Delhi NCR"})
    assert r.status_code == 201
    zone_id = r.json()["id"]
    listed = admin.get("/api/v1/zones").json()
    assert any(z["id"] == zone_id for z in listed)


# --- Admin user management & LMO-by-zone -------------------------------------


def test_users_admin_only(client_factory):
    lmo = client_factory("lmo@example.com", "lmo123")
    assert lmo.get("/api/v1/users").status_code == 403

    admin = client_factory("admin@example.com", "admin123")
    users = admin.get("/api/v1/users")
    assert users.status_code == 200
    roles = {u["role"] for u in users.json()}
    assert "ADMIN" in roles and "LMO" in roles


def test_admin_lists_lmos_by_zone(client_factory):
    admin = client_factory("admin@example.com", "admin123")
    # Assign the LMO to a zone
    users = admin.get("/api/v1/users").json()
    lmo = next(u for u in users if u["role"] == "LMO")
    zones = admin.get("/api/v1/zones").json()
    zone_id = zones[0]["id"] if zones else None
    assert zone_id, "expected at least one zone from prior test"

    upd = admin.patch(f"/api/v1/users/{lmo['id']}", json={"zone_id": zone_id})
    assert upd.status_code == 200
    assert upd.json()["zone_id"] == zone_id

    lmos = admin.get("/api/v1/admins/lmos").json()
    assert any(u["id"] == lmo["id"] and u["zone_id"] == zone_id for u in lmos)


def test_admin_dashboard_shows_lmos_by_zone(client_factory):
    admin = client_factory("admin@example.com", "admin123")
    r = admin.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "ADMIN"
    assert "stats" in body
    assert "lmos_by_zone" in body
    assert body["stats"]["total_users"] >= 5


# --- Products ----------------------------------------------------------------


def test_products_visibility(client_factory):
    consumer = client_factory("consumer@example.com", "consumer123")
    assert consumer.get("/api/v1/products").status_code == 403

    manufacturer = client_factory("manufacturer@example.com", "mfr123")
    resp = manufacturer.get("/api/v1/products")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_product_manufacturer(client_factory):
    manufacturer = client_factory("manufacturer@example.com", "mfr123")
    r = manufacturer.post(
        "/api/v1/products",
        json={"name": "Test Snack", "category": "FOOD", "subcategory": "FOOD_SNACKS", "brand": "TestBrand"},
    )
    assert r.status_code == 201
    pid = r.json()["id"]

    # Manufacturer can delete their own product
    d = manufacturer.delete(f"/api/v1/products/{pid}")
    assert d.status_code == 204


def test_retailer_cannot_create_product(client_factory):
    retailer = client_factory("retailer@example.com", "retail123")
    assert retailer.post("/api/v1/products", json={"name": "X", "category": "FOOD"}).status_code == 403


# --- Inspections (ADMIN / LMO) -----------------------------------------------


def test_inspection_lmo_only(client_factory):
    # Retailer cannot create inspections
    retailer = client_factory("retailer@example.com", "retail123")
    assert retailer.post("/api/v1/inspections", json={"analysis_id": "nope"}).status_code == 403

    # Create an analysis as manufacturer first
    mfr = client_factory("manufacturer@example.com", "mfr123")
    a = mfr.post("/api/v1/analyses", data={"category": "FOOD"})
    analysis_id = a.json()["analysis_id"]

    # LMO can create an inspection
    lmo = client_factory("lmo@example.com", "lmo123")
    r = lmo.post(
        "/api/v1/inspections",
        json={"analysis_id": analysis_id, "location": "Store #12", "observations": "Checked label"},
    )
    assert r.status_code == 201
    insp_id = r.json()["id"]

    # LMO can list their inspections and update status
    listed = lmo.get("/api/v1/inspections")
    assert any(i["id"] == insp_id for i in listed.json())

    upd = lmo.patch(f"/api/v1/inspections/{insp_id}", json={"status": "COMPLETED"})
    assert upd.status_code == 200
    assert upd.json()["status"] == "COMPLETED"


def test_dashboard_summary_lmo(client_factory):
    lmo = client_factory("lmo@example.com", "lmo123")
    r = lmo.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    assert r.json()["role"] == "LMO"
    assert "my_inspections" in r.json()["stats"]


def test_dashboard_summary_manufacturer(client_factory):
    mfr = client_factory("manufacturer@example.com", "mfr123")
    r = mfr.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    assert r.json()["role"] == "MANUFACTURER"
    assert "my_products" in r.json()["stats"]


# --- Cross-ownership protection ----------------------------------------------


def test_analysis_ownership_enforced(client_factory):
    # Manufacturer creates an analysis
    mfr = client_factory("manufacturer@example.com", "mfr123")
    a = mfr.post("/api/v1/analyses", data={"category": "FOOD"})
    analysis_id = a.json()["analysis_id"]

    # A different manufacturer cannot view/run the other's analysis
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models import User, UserRole

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "mfr2@example.com").first():
            other = User(
                email="mfr2@example.com",
                hashed_password=hash_password("mfr123"),
                full_name="Another Mfr",
                role=UserRole.MANUFACTURER,
                is_active=True,
            )
            db.add(other)
            db.commit()
    finally:
        db.close()

    other_client = client_factory("mfr2@example.com", "mfr123")
    # Fellow manufacturer's list shows their own (may be empty), never the
    # other one's analysis via a direct fetch/run.
    run = other_client.post(f"/api/v1/analyses/{analysis_id}/run")
    assert run.status_code == 403
