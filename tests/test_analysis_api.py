"""API integration tests for image upload and OCR endpoints.

These use the FastAPI TestClient against the real app and the real
PostgreSQL database (seeded via seed_db).
"""

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _make_analysis(client) -> str:
    resp = client.post("/api/v1/analyses", data={"category": "FOOD"})
    assert resp.status_code == 201
    return resp.json()["analysis_id"]


def test_create_analysis(client):
    analysis_id = _make_analysis(client)
    assert analysis_id


def test_upload_image_and_ocr(client):
    analysis_id = _make_analysis(client)
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        resp = client.post(
            f"/api/v1/analyses/{analysis_id}/images",
            files={"file": ("front.jpg", fh, "image/jpeg")},
            data={"position": "FRONT"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["image"]["image_position"] == "FRONT"
    assert body["image"]["file_path"]

    ocr_resp = client.post(f"/api/v1/analyses/{analysis_id}/ocr")
    assert ocr_resp.status_code == 200
    ocr = ocr_resp.json()
    assert ocr["status"] == "completed"
    assert ocr["image_count"] == 1
    assert isinstance(ocr["text_blocks"], list)
    assert "raw_text" in ocr
    assert 0.0 <= ocr["confidence"] <= 1.0


def test_upload_invalid_position(client):
    analysis_id = _make_analysis(client)
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        resp = client.post(
            f"/api/v1/analyses/{analysis_id}/images",
            files={"file": ("f.jpg", fh, "image/jpeg")},
            data={"position": "NOPE"},
        )
    assert resp.status_code == 422


def test_upload_non_image(client):
    analysis_id = _make_analysis(client)
    resp = client.post(
        f"/api/v1/analyses/{analysis_id}/images",
        files={"file": ("bad.txt", b"not an image", "text/plain")},
        data={"position": "FRONT"},
    )
    assert resp.status_code == 422


def test_ocr_no_images(client):
    analysis_id = _make_analysis(client)
    resp = client.post(f"/api/v1/analyses/{analysis_id}/ocr")
    assert resp.status_code == 400


def test_ocr_missing_analysis(client):
    resp = client.post("/api/v1/analyses/nonexistent/ocr")
    assert resp.status_code == 404


def test_upload_missing_analysis(client):
    with open(FIXTURES / "valid_tea.jpg", "rb") as fh:
        resp = client.post(
            "/api/v1/analyses/nonexistent/images",
            files={"file": ("f.jpg", fh, "image/jpeg")},
            data={"position": "FRONT"},
        )
    assert resp.status_code == 404
