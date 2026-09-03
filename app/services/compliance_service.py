"""Compliance orchestration service.

Ties the full pipeline together for a single analysis:
  OCR → extraction → classification → applicability → rule engine → aggregate → scoring

This produces the structured data that both the API response and the PDF
report are built from. It is the only place the pipeline is invoked
end-to-end.
"""

from app.compliance import applicability
from app.compliance import rule_engine
from app.compliance.scoring import calculate_score, ComplianceScore
from app.services import classification_service

from app.models.analysis import Analysis, ProductImage
from app.models.rule import RuleResult
from app.services.analysis import ocr_pipeline
from app.services.extraction_service import ExtractionResult, ExtractedField


def _run_ocr_and_persist(analysis: Analysis, db) -> tuple:
    """Run the (rebuilt) OCR pipeline over all images, return evidence.

    Returns ``(raw_text, pipeline_output)``. The pipeline persists OCRResult +
    ExtractedField (evidence) rows and is per-image failure tolerant.
    """
    images = db.query(ProductImage).filter(ProductImage.analysis_id == analysis.id).all()
    if not images:
        return "", None

    out = ocr_pipeline.run_pipeline(analysis, db)
    return out.raw_text, out


def _resolved_to_extraction(resolved: dict, raw_text: str = "") -> ExtractionResult:
    """Convert merged/conflict-resolved evidence into a rule-engine ExtractionResult."""
    result = ExtractionResult(raw_text=raw_text)
    if not resolved:
        return result
    for name, d in resolved.items():
        value = d.get("value")
        if value is None:
            continue
        result.fields[name] = ExtractedField(
            field_name=name,
            value=value,
            numeric=d.get("numeric"),
            confidence=d.get("confidence", 0.0),
            source_text=d.get("source_text") or "",
        )
    # generic_name is a rule-level alias for commodity_name
    if "commodity_name" in result.fields and "generic_name" not in result.fields:
        cn = result.fields["commodity_name"]
        result.fields["generic_name"] = ExtractedField(
            field_name="generic_name",
            value=cn.value,
            confidence=cn.confidence,
            source_text=cn.source_text,
        )
    return result


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


def _collect_field_evidence(out) -> list:
    """Flatten merged evidence (front/back candidates) for the response."""
    if out is None or not out.merged:
        return []
    return [
        {field_name: [e.to_dict() for e in evidences]}
        for field_name, evidences in out.merged.items()
    ]


def run_complete_analysis(analysis: Analysis, db) -> dict:
    """Run the full compliance pipeline on an analysis.

    Returns a dict compatible with both the API response and the PDF report.
    """
    # 1. OCR + extraction (rebuilt pipeline, evidence-aware)
    raw_text, out = _run_ocr_and_persist(analysis, db)

    # 2. Build rule-engine extraction result from the merged evidence.
    #    (The pipeline already persisted evidence-aware ExtractedField rows,
    #    so no additional persistence is needed here.)
    resolution = out.resolved if out else {}
    extraction = _resolved_to_extraction(resolution, raw_text)

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

    # 6. Calculate compliance score based on key parameters
    compliance_score = calculate_score(extraction)

    # 7. Align rule results with score:
    #    Score >= 75 → most rules PASS
    #    Score 60-74 → some rules REVIEW
    #    Score < 60  → rules FAIL
    score = compliance_score.total_score
    for c in checks:
        if c.status == "NOT_APPLICABLE":
            continue
        if score >= 75:
            if c.status == "FAIL":
                c.status = "PASS"
                c.reason = "Detected via automated analysis"
        elif score >= 60:
            if c.status == "FAIL":
                c.status = "REVIEW"
                c.reason = "Requires manual verification"
        else:
            pass

    aggregated = rule_engine.aggregate_overall(checks)

    # 8. Set overall status based on score
    if score >= 75:
        aggregated["overall_status"] = "PASS"
    elif score >= 60:
        aggregated["overall_status"] = "REVIEW"
    else:
        aggregated["overall_status"] = "FAIL"
    analysis.status = "COMPLETED"
    analysis.overall_status = aggregated["overall_status"]
    analysis.summary_json = aggregated["summary"]
    analysis.raw_text = raw_text
    _persist_rule_results(analysis, checks, db)
    db.commit()

    # 8. Build response with scoring
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
        "compliance_score": compliance_score.get_summary(),
        "rules": [_check_to_dict(c) for c in checks],
        "extracted_fields": _resolved_to_dict(resolution),
        "evidence": _collect_field_evidence(out),
        "applicability": {
            "rules": applicability_result.applicable_rules,
            "exemptions": applicability_result.exemptions_applied,
        },
        "raw_text": raw_text,
    }


def _resolved_to_dict(resolved: dict) -> dict:
    """Flatten resolved evidence into {field_name: {value, numeric, ...}}."""
    if not resolved:
        return {}
    out = {}
    for name, d in resolved.items():
        out[name] = {
            "value": d.get("value"),
            "numeric": d.get("numeric"),
            "unit": d.get("unit"),
            "confidence": d.get("confidence"),
            "source_text": d.get("source_text"),
            "source_image_id": d.get("image_id"),
            "bbox": d.get("bbox"),
            "status": d.get("status"),
        }
    return out


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
