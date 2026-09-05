"""Demo script: run the full compliance pipeline on one or more fixture images
and print the structured output. Used to demonstrate the core to the user.

Usage:
  python scripts/demo_scan.py images.jpg                 # single image
  python scripts/demo_scan.py front.jpg back.jpg side    # front/back/side
"""

import json
import sys
from pathlib import Path

# Allow running as `python scripts/demo_scan.py` from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def run_analysis(files: list[tuple[str, str]]) -> dict:
    """files: list of (filename, position). Uploads all, runs the pipeline."""
    client = TestClient(app)
    r = client.post("/api/v1/analyses", data={"category": "FOOD"})
    aid = r.json()["analysis_id"]

    for name, position in files:
        with open(FIXTURES / name, "rb") as fh:
            up = client.post(
                f"/api/v1/analyses/{aid}/images",
                files={"file": (name, fh, "image/jpeg")},
                data={"position": position},
            )
        if up.status_code != 201:
            print(f"Upload failed for {name}: {up.status_code} {up.text}")
            sys.exit(1)

    data = client.post(f"/api/v1/analyses/{aid}/run").json()
    data["_analysis_id"] = aid
    return data


def display(data: dict):
    print("=" * 70)
    print("  PACKAGED COMMODITY COMPLIANCE SCAN")
    print("=" * 70)
    print(f"  Analysis ID : {data.get('_analysis_id')}")
    p = data.get("product", {})
    print(f"  Product     : {p.get('name')}")
    print(f"  Category    : {p.get('category')} / {p.get('subcategory')}")

    overall = data.get("overall_status")
    print(f"\n  OVERALL STATUS: {overall}")
    s = data.get("summary", {})
    print(f"  PASS {s.get('PASS',0)} | FAIL {s.get('FAIL',0)} | "
          f"REVIEW {s.get('REVIEW',0)} | NOT_APPLICABLE {s.get('NOT_APPLICABLE',0)}")

    print("\n  Extracted fields:")
    for name, f in data.get("extracted_fields", {}).items():
        if f.get("value"):
            print(f"    - {name}: {f['value']}")

    print("\n  Rule results:")
    for r in data.get("rules", []):
        print(f"    Rule {r['rule']:>2} | {r['status']:<14} | {r['title']}")
        print(f"         -> {r['reason']}")

    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Optional: pairs of "filename position"; default position FRONT
        files = []
        for arg in sys.argv[1:]:
            parts = arg.split(":")
            name = parts[0]
            pos = parts[1].upper() if len(parts) > 1 else "FRONT"
            files.append((name, pos))
    else:
        files = [("valid_tea.jpg", "FRONT")]

    data = run_analysis(files)
    display(data)

    # Also generate the PDF report
    client = TestClient(app)
    rep = client.get(f"/api/v1/analyses/{data['_analysis_id']}/report")
    print(f"\nPDF report: HTTP {rep.status_code}, {len(rep.content)} bytes, "
          f"content-type={rep.headers['content-type']}")
    if rep.status_code == 200:
        out = Path("reports") / f"demo_analysis_{data['_analysis_id']}.pdf"
        out.write_bytes(rep.content)
        print(f"Saved to {out}")
