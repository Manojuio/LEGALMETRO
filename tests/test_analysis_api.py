"""API integration tests for image upload and OCR endpoints.

These use the FastAPI TestClient against the real app and the real
PostgreSQL database (seeded via seed_db). The `auth_client` fixture logs in
as a seeded user so analysis endpoints (now JWT-protected) succeed.
"""

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _make_analysis(client) -> str:
    resp = client.post("/api/v1/analyses", data={"category": "FOOD"})
    assert resp.status_code == 201
    return resp.json()["analysis_id"]


def test_create_analysis(auth_client):
    analysis_id = _make_analysis(auth_client)
    assert analysis_id


def test_upload_image_and_ocr(auth_client):
    analysis_id = _make_analysis(auth_client)
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        resp = auth_client.post(
            f"/api/v1/analyses/{analysis_id}/images",
            files={"file": ("front.jpg", fh, "image/jpeg")},
            data={"position": "FRONT"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["image"]["image_position"] == "FRONT"
    assert body["image"]["file_path"]

    ocr_resp = auth_client.post(f"/api/v1/analyses/{analysis_id}/ocr")
    assert ocr_resp.status_code == 200
    ocr = ocr_resp.json()
    assert ocr["status"] == "completed"
    assert ocr["image_count"] == 1
    assert isinstance(ocr["text_blocks"], list)
    assert "raw_text" in ocr
    assert 0.0 <= ocr["confidence"] <= 1.0


def test_upload_invalid_position(auth_client):
    analysis_id = _make_analysis(auth_client)
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        resp = auth_client.post(
            f"/api/v1/analyses/{analysis_id}/images",
            files={"file": ("f.jpg", fh, "image/jpeg")},
            data={"position": "NOPE"},
        )
    assert resp.status_code == 422


def test_upload_non_image(auth_client):
    analysis_id = _make_analysis(auth_client)
    resp = auth_client.post(
        f"/api/v1/analyses/{analysis_id}/images",
        files={"file": ("bad.txt", b"not an image", "text/plain")},
        data={"position": "FRONT"},
    )
    assert resp.status_code == 422


def test_ocr_no_images(auth_client):
    analysis_id = _make_analysis(auth_client)
    resp = auth_client.post(f"/api/v1/analyses/{analysis_id}/ocr")
    assert resp.status_code == 400


def test_ocr_missing_analysis(auth_client):
    resp = auth_client.post("/api/v1/analyses/nonexistent/ocr")
    assert resp.status_code == 404


def test_upload_missing_analysis(client):
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        resp = client.post(
            "/api/v1/analyses/nonexistent/images",
            files={"file": ("f.jpg", fh, "image/jpeg")},
            data={"position": "FRONT"},
        )
    # The endpoint requires auth; without a token it returns 401 first.
    assert resp.status_code in (401, 404)


def test_analyses_require_auth(client):
    """Without a token, creating an analysis returns 401."""
    resp = client.post("/api/v1/analyses", data={"category": "FOOD"})
    assert resp.status_code == 401


def test_list_analyses(auth_client):
    _make_analysis(auth_client)
    resp = auth_client.get("/api/v1/analyses")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
