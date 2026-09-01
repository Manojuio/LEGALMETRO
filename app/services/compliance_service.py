"""Compliance orchestration service.

Ties the full pipeline together for a single analysis:
  OCR → extraction → classification → applicability → rule engine → aggregate

This produces the structured data that both the API response and the PDF
report are built from. It is the only place the pipeline is invoked
end-to-end.
"""

from app.compliance import applicability
from app.compliance import rule_engine
from app.services import classification_service, extraction_service, ocr_service, image_service

from app.models.analysis import Analysis, ProductImage, OCRResult, ExtractedField
from app.models.rule import RuleResult


def _ocr_raw_text(analysis: Analysis, db) -> str:
    """Return combined raw OCR text by (re)running OCR if needed, else reuse."""
    # Try to reuse already-persisted OCR results
    existing = db.query(OCRResult).filter(OCRResult.analysis_id == analysis.id).all()
    if existing:
        parts = [r.raw_text for r in existing if r.raw_text]
        return "\n".join(parts)

    return ""


def _run_ocr_and_persist(analysis: Analysis, db) -> str:
    """Run OCR on all images (if no OCR yet), persist results, return text."""
    images = db.query(ProductImage).filter(ProductImage.analysis_id == analysis.id).all()
    if not images:
        return ""

    combined = []
    for img in images:
        with open(img.file_path, "rb") as fh:
            data = fh.read()
        pre = image_service.preprocess(data)
        result = ocr_service.run_ocr(pre.grayscale, pre.steps_applied)

        ocr_row = OCRResult(
            analysis_id=analysis.id,
            image_id=img.id,
            raw_text=result.raw_text,
            text_blocks=[
                {"text": b.text, "confidence": b.confidence, "bbox": b.bbox}
                for b in result.blocks
            ],
            confidence_score=result.confidence_score,
            processing_time_ms=result.processing_time_ms,
            ocr_engine=result.engine,
        )
        db.add(ocr_row)
        if result.raw_text:
            combined.append(result.raw_text)

    db.commit()
    return "\n".join(combined)


def _persist_extraction(analysis: Analysis, extraction, db):
    # Remove old extracted fields to avoid duplicates on re-run
    db.query(ExtractedField).filter(ExtractedField.analysis_id == analysis.id).delete()
    for name, f in extraction.fields.items():
        db.add(
            ExtractedField(
                analysis_id=analysis.id,
                field_name=name,
                field_value=f.value,
                field_value_numeric=f.numeric,
                confidence=f.confidence,
                source_text=f.source_text,
                extraction_method="regex",
            )
        )
    db.commit()


def _persist_rule_results(analysis: Analysis, checks, db):
    db.query(RuleResult).filter(RuleResult.analysis_id == analysis.id).delete()
    for c in checks:
        db.add(
            RuleResult(
                analysis_id=analysis.id,
                rule_id=c.rule_id,
                status=c.status,
                reason=c.reason,
                confidence=c.confidence,
                validator_name=c.validation_type,
            )
        )
    db.commit()


def run_complete_analysis(analysis: Analysis, db) -> dict:
    """Run the full compliance pipeline on an analysis.

    Returns a dict compatible with both the API response and the PDF report.
    """
    # 1. OCR (reuse if already run)
    raw_text = _run_ocr_and_persist(analysis, db)

    # 2. Extraction
    extraction = extraction_service.run_extraction(raw_text)
    _persist_extraction(analysis, extraction, db)

    # 3. Classification
    commodity = extraction.get("commodity_name")
    classification = classification_service.classify(
        commodity.value if commodity else None,
        raw_text,
    )
    analysis.category = classification.category
    analysis.subcategory = classification.subcategory

    # 4. Applicability + exemptions
    context = {
        "is_imported": False,
        "sale_type": "RETAIL",
        "package_type": "RETAIL",
        "category": classification.category,
    }
    applicability_result = applicability.determine_applicability(
        classification.applicable_rules,
        context,
    )

    # 5. Rule engine
    checks = rule_engine.run_rules(
        extraction,
        applicability_result.applicable_rules,
        classification.category,
    )
    aggregated = rule_engine.aggregate_overall(checks)

    # 6. Persist analysis metadata + results
    analysis.status = "COMPLETED"
    analysis.overall_status = aggregated["overall_status"]
    analysis.summary_json = aggregated["summary"]
    _persist_rule_results(analysis, checks, db)
    db.commit()

    # 7. Build response
    return {
        "analysis_id": analysis.id,
        "product": {
            "name": classification.name,
            "category": classification.category,
            "subcategory": classification.subcategory,
            "classification_confidence": classification.confidence,
        },
        "overall_status": aggregated["overall_status"],
        "summary": aggregated["summary"],
        "rules": [_check_to_dict(c) for c in checks],
        "extracted_fields": extraction_service.extraction_to_dict(extraction),
        "applicability": {
            "rules": applicability_result.applicable_rules,
            "exemptions": applicability_result.exemptions_applied,
        },
        "raw_text": raw_text,
    }


def _check_to_dict(check) -> dict:
    return {
        "rule": check.rule_number,
        "rule_id": check.rule_id,
        "title": check.title,
        "category": check.category,
        "severity": check.severity,
        "status": check.status,
        "reason": check.reason,
        "evidence": check.evidence,
        "confidence": check.confidence,
    }
