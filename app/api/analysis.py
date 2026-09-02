"""Analysis endpoints: create analysis, upload images, run OCR.

Phase 9+ — analysis lifecycle with JWT/RBAC protection.
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.analysis import (
    Analysis,
    AnalysisStatus,
    ImagePosition,
    OCRResult,
    ProductImage,
)
from app.models.user import User
from app.schemas.image import OCRResponse, UploadedImageResponse
from app.services import image_service, ocr_service, compliance_service, report_service

router = APIRouter()


def _get_owned_analysis(analysis_id: str, user: User, db: Session) -> Analysis:
    """Return an analysis, enforcing that the user may access it.

    Admin/LMO can view any analysis; other roles can only access their own.
    """
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if user.role.value in ("ADMIN", "LMO"):
        return analysis
    if analysis.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your analysis")
    return analysis


@router.get(
    "/analyses",
    summary="List analyses visible to the current user",
    tags=["analysis"],
)
def list_analyses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return analyses the current user is allowed to see.

    - ADMIN/LMO: all analyses across every user
    - MANUFACTURER/RETAILER/CONSUMER: only their own analyses
    """
    if current_user.role.value in ("ADMIN", "LMO"):
        analyses = db.query(Analysis).order_by(Analysis.created_at.desc()).all()
    else:
        analyses = (
            db.query(Analysis)
            .filter(Analysis.user_id == current_user.id)
            .order_by(Analysis.created_at.desc())
            .all()
        )
    return [
        {
            "id": a.id,
            "status": a.status.value,
            "overall_status": a.overall_status.value if a.overall_status else None,
            "category": a.category,
            "subcategory": a.subcategory,
            "summary": a.summary_json,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in analyses
    ]


@router.post(
    "/analyses",
    status_code=201,
    summary="Create a new analysis",
    tags=["analysis"],
)
def create_analysis(
    category: str | None = Form(default=None),
    subcategory: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an empty analysis owned by the current authenticated user.

    Images can then be uploaded to this analysis.
    """
    analysis = Analysis(
        user_id=current_user.id,
        category=category,
        subcategory=subcategory,
        status=AnalysisStatus.PENDING,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return {"analysis_id": analysis.id, "status": analysis.status.value}


@router.post(
    "/analyses/{analysis_id}/images",
    status_code=201,
    summary="Upload a product image to an analysis",
    tags=["analysis"],
)
def upload_image(
    analysis_id: str,
    file: UploadFile = File(...),
    position: str = Form(default="OTHER"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadedImageResponse:
    """Validate and store one image for the analysis.

    Limits: file type, size, decodability are enforced here. The binary is
    stored on disk under uploads/analysis_<id>/; only metadata is persisted.
    """
    analysis = _get_owned_analysis(analysis_id, current_user, db)

    try:
        position_enum = ImagePosition[position.upper()]
    except KeyError:
        valid = [p.name for p in ImagePosition]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid position '{position}'. Valid: {valid}",
        )

    position_lower = position_enum.value.lower()

    data = file.file.read()
    try:
        absolute_path, metadata = image_service.save_upload(
            analysis_id=analysis_id,
            data=data,
            position=position_lower,
            original_filename=file.filename or "upload.jpg",
        )
    except image_service.ImageValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    product_image = ProductImage(
        analysis_id=analysis_id,
        filename=metadata["filename"],
        file_path=metadata["saved_path"],
        file_size=metadata["size_bytes"],
        mime_type=metadata["mime_type"],
        image_position=position_enum,
        width=metadata.get("width"),
        height=metadata.get("height"),
    )
    db.add(product_image)
    analysis.status = AnalysisStatus.PROCESSING
    db.commit()
    db.refresh(product_image)

    return UploadedImageResponse(
        analysis_id=analysis_id,
        image={
            "id": product_image.id,
            "filename": product_image.filename,
            "file_path": product_image.file_path,
            "file_size": product_image.file_size,
            "mime_type": product_image.mime_type,
            "image_position": product_image.image_position.value,
            "width": product_image.width,
            "height": product_image.height,
        },
    )


@router.post(
    "/analyses/{analysis_id}/ocr",
    summary="Run OCR on all uploaded images for an analysis",
    tags=["analysis"],
)
def run_ocr(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run the OCR pipeline on every image attached to the analysis.

    Returns the combined OCR output. Each image is preprocessed then passed
    to EasyOCR. Raw text, per-block confidence, and bounding boxes are
    persisted as evidence — NOT used to make compliance decisions here.
    """
    analysis = _get_owned_analysis(analysis_id, current_user, db)

    images = db.query(ProductImage).filter(ProductImage.analysis_id == analysis_id).all()
    if not images:
        raise HTTPException(status_code=400, detail="No images uploaded to this analysis")

    combined_blocks = []
    combined_text_parts = []
    confidence_sum = 0.0
    count = 0

    for img in images:
        file_path = img.file_path
        with open(file_path, "rb") as fh:
            data = fh.read()

        preprocessed = image_service.preprocess(data)
        result = ocr_service.run_ocr(preprocessed.grayscale, preprocessed.steps_applied)

        # Persist OCR result as evidence
        ocr_row = OCRResult(
            analysis_id=analysis_id,
            image_id=img.id,
            raw_text=result.raw_text,
            text_blocks=[
                {
                    "text": b.text,
                    "confidence": b.confidence,
                    "bbox": b.bbox,
                }
                for b in result.blocks
            ],
            confidence_score=result.confidence_score,
            processing_time_ms=result.processing_time_ms,
            ocr_engine=result.engine,
        )
        db.add(ocr_row)

        for block in result.blocks:
            combined_blocks.append(
                {
                    "image_id": img.id,
                    "position": img.image_position.value,
                    "text": block.text,
                    "confidence": block.confidence,
                    "bbox": block.bbox,
                }
            )
        if result.raw_text:
            combined_text_parts.append(result.raw_text)
        if result.confidence_score > 0:
            confidence_sum += result.confidence_score
            count += 1

    db.commit()

    overall_confidence = round(confidence_sum / count, 4) if count else 0.0

    return {
        "status": "completed",
        "analysis_id": analysis_id,
        "text_blocks": combined_blocks,
        "raw_text": "\n".join(combined_text_parts),
        "confidence": overall_confidence,
        "image_count": len(images),
    }


@router.post(
    "/analyses/{analysis_id}/run",
    summary="Run the complete compliance analysis (OCR → extraction → validation)",
    tags=["analysis"],
)
def run_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Orchestrate the full compliance pipeline and return structured results.

    1. Run OCR (reuses already-persisted OCR if present)
    2. Extract structured fields
    3. Classify product
    4. Determine applicable rules (+ exemptions)
    5. Run deterministic rule validators
    6. Aggregate into PASS / FAIL / REVIEW
    7. Persist results
    """
    analysis = _get_owned_analysis(analysis_id, current_user, db)

    return compliance_service.run_complete_analysis(analysis, db)


@router.get(
    "/analyses/{analysis_id}/report",
    summary="Generate a PDF compliance report",
    tags=["analysis"],
)
def generate_report(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and return a PDF compliance report for the analysis.

    If the analysis has no results yet, it is not auto-run here; the client
    should call /run first. Returns the PDF file as a download.
    """
    analysis = _get_owned_analysis(analysis_id, current_user, db)

    if analysis.overall_status is None:
        raise HTTPException(
            status_code=400,
            detail="Analysis has no results — call POST /run first",
        )

    # Build the data dict from persisted state
    from app.models.rule import RuleResult, Rule
    rule_results = (
        db.query(RuleResult, Rule)
        .join(Rule, Rule.id == RuleResult.rule_id)
        .filter(RuleResult.analysis_id == analysis_id)
        .all()
    )
    checks = [
        {
            "rule_number": rule.rule_number,
            "title": rule.title,
            "category": rule.category,
            "status": rr.status,
            "reason": rr.reason or "",
        }
        for rr, rule in rule_results
    ]

    # Get extracted fields to calculate scoring
    from app.models.analysis import ExtractedField as ExtractedFieldModel
    from app.services.extraction_service import ExtractionResult, ExtractedField
    
    extracted_fields = db.query(ExtractedFieldModel).filter(
        ExtractedFieldModel.analysis_id == analysis_id
    ).all()
    
    # Reconstruct extraction result for scoring
    extraction = ExtractionResult(raw_text="")
    for ef in extracted_fields:
        extraction.fields[ef.field_name] = ExtractedField(
            field_name=ef.field_name,
            value=ef.field_value,
            numeric=ef.field_value_numeric,
            confidence=ef.confidence,
            source_text=ef.source_text or "",
        )
    
    # Calculate compliance score
    from app.compliance.scoring import calculate_score
    compliance_score = calculate_score(extraction)

    summary = analysis.summary_json or {}
    analysis_data = {
        "analysis_id": analysis.id,
        "product": {
            "name": analysis.category or "Unknown",
            "category": f"{analysis.category} / {analysis.subcategory}",
            "subcategory": analysis.subcategory or "",
            "classification_confidence": 0.9,
        },
        "overall_status": analysis.overall_status.value,
        "summary": summary,
        "compliance_score": compliance_score.get_summary(),
        "rules": checks,
    }

    generator = report_service.ReportGenerator()
    try:
        report_path = generator.generate(analysis_data, compliance_score)
    except Exception as exc:  # pragma: no cover - report build failure
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(report_path),
        media_type="application/pdf",
        filename=f"analysis_{analysis.id}.pdf",
    )
