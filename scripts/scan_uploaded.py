"""Run the full compliance pipeline on a user-supplied image from the root,
bypassing HTTP auth by using the ORM + compliance_service directly."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.analysis import Analysis, AnalysisStatus, ImagePosition, ProductImage
from app.models.user import User, UserRole
from app.services import image_service, compliance_service

IMG = Path(__file__).resolve().parent.parent / "image.png"


def get_any_user(db):
    user = db.query(User).filter(User.role == UserRole.LMO).first()
    if user is None:
        user = db.query(User).first()
    return user


def main():
    if not IMG.exists():
        print(f"Image not found: {IMG}")
        return

    db = SessionLocal()
    try:
        user = get_any_user(db)
        if user is None:
            print("No user found in DB. Run: python -m scripts.seed_db")
            return
        print(f"Using user: {user.email} ({user.role.value})")

        analysis = Analysis(
            user_id=user.id,
            category="FOOD",
            subcategory=None,
            status=AnalysisStatus.PENDING,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        aid = analysis.id
        print(f"Created analysis: {aid}")

        data = IMG.read_bytes()
        absolute_path, metadata = image_service.save_upload(
            analysis_id=aid,
            data=data,
            position="front",
            original_filename=IMG.name,
        )
        product_image = ProductImage(
            analysis_id=aid,
            filename=metadata["filename"],
            file_path=metadata["saved_path"],
            file_size=metadata["size_bytes"],
            mime_type=metadata["mime_type"],
            image_position=ImagePosition.FRONT,
            width=metadata.get("width"),
            height=metadata.get("height"),
        )
        db.add(product_image)
        analysis.status = AnalysisStatus.PROCESSING
        db.commit()
        print("Image uploaded.")

        t0 = time.time()
        data = compliance_service.run_complete_analysis(analysis, db)
        print(f"Run took {time.time() - t0:.1f}s")
    finally:
        db.close()

    print("=" * 72)
    print("  RAW OCR TEXT")
    print("=" * 72)
    raw = data.get("raw_text", "")
    print(raw if raw else "(no text detected)")

    print("=" * 72)
    print("  CLASSIFICATION")
    print("=" * 72)
    p = data.get("product", {})
    print(f"  Name       : {p.get('name')}")
    print(f"  Category   : {p.get('category')} / {p.get('subcategory')}")
    print(f"  Confidence : {p.get('classification_confidence')}")

    print("=" * 72)
    print("  OVERALL STATUS: " + str(data.get("overall_status")))
    s = data.get("summary", {})
    print(f"  PASS {s.get('PASS',0)} | FAIL {s.get('FAIL',0)} | "
          f"REVIEW {s.get('REVIEW',0)} | NOT_APPLICABLE {s.get('NOT_APPLICABLE',0)}")

    print("=" * 72)
    print("  COMPLIANCE SCORE  (/100)")
    print("=" * 72)
    sc = data.get("compliance_score", {})
    print(f"  TOTAL  : {sc.get('total_score')} / 100  (grade {sc.get('grade')}, "
          f"compliant={sc.get('is_compliant')})")
    ess = sc.get("essential", {})
    sup = sc.get("supporting", {})
    print(f"  ESSENTIAL ({ess.get('passed')}/{ess.get('count')} passed): "
          f"{ess.get('score')}/{ess.get('max')} pts = {ess.get('percentage')}%")
    print(f"  SUPPORTING ({sup.get('passed')}/{sup.get('count')} passed): "
          f"{sup.get('score')}/{sup.get('max')} pts = {sup.get('percentage')}%")

    print("=" * 72)
    print("  EXTRACTED FIELDS")
    print("=" * 72)
    for name, f in data.get("extracted_fields", {}).items():
        if f.get("value"):
            print(f"    - {name}: {f['value']}  (conf {f.get('confidence')})")

    print("=" * 72)
    print("  RULE RESULTS")
    print("=" * 72)
    for r in data.get("rules", []):
        print(f"    Rule {r['rule']:>2} [{r['severity']}] | {r['status']:<12} | {r['title']}")
        print(f"         -> {r['reason']}")

    print("=" * 72)


if __name__ == "__main__":
    main()
