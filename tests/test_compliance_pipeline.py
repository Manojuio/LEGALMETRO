"""End-to-end test of the complete compliance pipeline.

Uploads fixture images, runs /run, and verifies the structured output.
Also generates a PDF report and checks it exists. Uses an authenticated
client (seeded user) because analysis endpoints are JWT-protected.
"""

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _create_and_upload(client, name: str, position: str) -> str:
    resp = client.post("/api/v1/analyses", data={"category": "FOOD"})
    assert resp.status_code == 201
    analysis_id = resp.json()["analysis_id"]
    with open(FIXTURES / name, "rb") as fh:
        up = client.post(
            f"/api/v1/analyses/{analysis_id}/images",
            files={"file": (name, fh, "image/jpeg")},
            data={"position": position},
        )
    assert up.status_code == 201, up.text
    return analysis_id


def test_full_pipeline_tea(auth_client):
    analysis_id = _create_and_upload(auth_client, "valid_tea.jpg", "FRONT")

    resp = auth_client.post(f"/api/v1/analyses/{analysis_id}/run")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["overall_status"] in ("PASS", "FAIL", "REVIEW")
    assert "summary" in data
    assert isinstance(data["rules"], list)
    assert len(data["rules"]) > 0
    assert "extracted_fields" in data
    assert "product" in data

    for r in data["rules"]:
        assert r["status"] in ("PASS", "FAIL", "REVIEW", "NOT_APPLICABLE")
        assert isinstance(r["reason"], str)

    counts = {"PASS": 0, "FAIL": 0, "REVIEW": 0, "NOT_APPLICABLE": 0}
    for r in data["rules"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    assert counts["PASS"] == data["summary"].get("PASS", 0)
    assert counts["FAIL"] == data["summary"].get("FAIL", 0)
    return data


def test_report_generation_after_run(auth_client):
    analysis_id = _create_and_upload(auth_client, "valid_biscuits.jpg", "FRONT")
    run = auth_client.post(f"/api/v1/analyses/{analysis_id}/run")
    assert run.status_code == 200

    rep = auth_client.get(f"/api/v1/analyses/{analysis_id}/report")
    assert rep.status_code == 200
    assert rep.headers["content-type"].startswith("application/pdf")
    body = rep.content

    assert body.startswith(b"%PDF")
    assert len(body) > 1000


def test_report_without_run_fails(auth_client):
    analysis_id = _create_and_upload(auth_client, "valid_tea.jpg", "FRONT")
    rep = auth_client.get(f"/api/v1/analyses/{analysis_id}/report")
    assert rep.status_code == 400


def test_missing_declarations_reports_fails(auth_client):
    analysis_id = _create_and_upload(auth_client, "missing_declarations.jpg", "FRONT")
    resp = auth_client.post(f"/api/v1/analyses/{analysis_id}/run")
    assert resp.status_code == 200
    data = resp.json()
    fail_statuses = [r["status"] for r in data["rules"]]
    assert "FAIL" in fail_statuses
