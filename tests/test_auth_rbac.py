"""Role-based access control tests for auth, products, and inspections.

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


def test_register_lmo_allowed(client):
    import uuid
    email = f"newlmo{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "pass123",
            "full_name": "New LMO",
            "role": "LMO",
        },
    )
    assert r.status_code == 201
    assert r.json()["role"] == "LMO"


def test_register_lmo_allowed_no_zone_required(client):
    """LMO registration no longer requires selecting a zone."""
    import uuid
    email = f"nolmo{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass123", "full_name": "No Zone", "role": "LMO"},
    )
    assert r.status_code == 201


def test_register_admin_forbidden(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "hacker@example.com", "password": "pass123", "full_name": "H", "role": "ADMIN"},
    )
    assert r.status_code == 403


# --- Admin user management & all-LMO listing ---------------------------------


def test_users_admin_only(client_factory):
    lmo = client_factory("lmo@example.com", "lmo123")
    assert lmo.get("/api/v1/users").status_code == 403

    admin = client_factory("admin@example.com", "admin123")
    users = admin.get("/api/v1/users")
    assert users.status_code == 200
    roles = {u["role"] for u in users.json()}
    assert "ADMIN" in roles and "LMO" in roles


def test_admin_lists_all_lmos(client_factory):
    admin = client_factory("admin@example.com", "admin123")
    lmos = admin.get("/api/v1/admins/lmos").json()
    assert any(u["role"] == "LMO" for u in lmos)


def test_admin_dashboard_shows_all_lmos(client_factory):
    admin = client_factory("admin@example.com", "admin123")
    r = admin.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "ADMIN"
    assert "stats" in body
    assert "lmos" in body
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


# --- Admin transparency: sees LMO analyses ----------------------------------


def test_admin_sees_only_lmo_analyses(client, client_factory):
    import uuid

    # Register + log in a fresh LMO.
    lmo_email = f"anlmo{uuid.uuid4().hex[:8]}@example.com"
    rr = client.post(
        "/api/v1/auth/register",
        json={
            "email": lmo_email,
            "password": "lmo123",
            "full_name": "LMO",
            "role": "LMO",
        },
    )
    assert rr.status_code == 201, rr.text
    admin = client_factory("admin@example.com", "admin123")
    lmo = client_factory(lmo_email, "lmo123")
    lmo_analysis_id = lmo.post("/api/v1/analyses", data={"category": "FOOD"}).json()["analysis_id"]

    # A manufacturer creates another analysis that admin must NOT see.
    mfr = client_factory("manufacturer@example.com", "mfr123")
    mfr_analysis_id = mfr.post("/api/v1/analyses", data={"category": "BEVERAGE"}).json()["analysis_id"]

    admin_analyses = admin.get("/api/v1/analyses")
    assert admin_analyses.status_code == 200
    by_id = {a["id"]: a for a in admin_analyses.json()}

    assert lmo_analysis_id in by_id
    assert by_id[lmo_analysis_id]["owner"]["role"] == "LMO"

    # Admin must NOT see the manufacturer's analysis.
    assert mfr_analysis_id not in by_id


def test_admin_cannot_run_or_create_analyses(client, client_factory):
    import uuid

    admin = client_factory("admin@example.com", "admin123")
    mfr = client_factory("manufacturer@example.com", "mfr123")

    # Admin cannot create a new analysis.
    created = admin.post("/api/v1/analyses", data={"category": "FOOD"})
    assert created.status_code == 403

    # Admin cannot run the full pipeline on an analysis either.
    analysis_id = mfr.post("/api/v1/analyses", data={"category": "FOOD"}).json()["analysis_id"]
    run = admin.post(f"/api/v1/analyses/{analysis_id}/run")
    assert run.status_code == 403

    # Admin can still fetch the generated report (read-only transparency).
    report = admin.get(f"/api/v1/analyses/{analysis_id}/report")
    # No results yet on a fresh run-less analysis -> reflects "no results" state.
    assert report.status_code in (200, 400)
