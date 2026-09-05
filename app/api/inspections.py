"""Inspection workflow endpoints (Phase 18).

An Inspection attaches an LMO field inspection (location, observations,
status) to an existing analysis. Only ADMIN and LMO can create/manage
inspections, per the roles matrix.

Also exposes:
- dashboard summary endpoint used by the LMO / ADMIN dashboards
- inspection-history endpoint with joins to analysis/product data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import (
    Analysis,
    Inspection,
    InspectionStatus,
    RuleResult,
    User,
    UserRole,
    Report,
    ExtractedField,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class InspectionCreate(BaseModel):
    analysis_id: str
    location: str | None = None
    observations: str | None = None
    notes: str | None = None


class InspectionUpdate(BaseModel):
    location: str | None = None
    observations: str | None = None
    notes: str | None = None
    status: InspectionStatus | None = None


class InspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    user_id: str
    location: str | None
    status: InspectionStatus
    overall_status: str | None = None
    observations: str | None
    notes: str | None
    created_at: object | None = None


class InspectionHistoryItem(BaseModel):
    """Denormalised inspection row for the history table."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    product_name: str | None = None
    product_category: str | None = None
    inspector_name: str | None = None
    inspector_id: str | None = None
    overall_status: str | None = None
    compliance_score: float | None = None
    created_at: object | None = None
    report_available: bool = False


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post(
    "/inspections",
    response_model=InspectionOut,
    status_code=201,
    tags=["inspections"],
    summary="Create an inspection (ADMIN / LMO)",
)
def create_inspection(
    payload: InspectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.LMO)),
) -> InspectionOut:
    analysis = db.get(Analysis, payload.analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    inspection = Inspection(
        analysis_id=payload.analysis_id,
        user_id=user.id,
        location=payload.location,
        observations=payload.observations,
        notes=payload.notes,
        status=InspectionStatus.PENDING,
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return InspectionOut.model_validate(inspection)


@router.get(
    "/inspections",
    response_model=list[InspectionOut],
    tags=["inspections"],
    summary="List inspections (ADMIN / LMO)",
)
def list_inspections(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.LMO)),
) -> list[InspectionOut]:
    # LMO sees their own inspections; ADMIN sees all.
    query = db.query(Inspection).order_by(Inspection.created_at.desc())
    if user.role == UserRole.LMO:
        query = query.filter(Inspection.user_id == user.id)
    return [InspectionOut.model_validate(i) for i in query.all()]


@router.get(
    "/inspections/history",
    response_model=list[InspectionHistoryItem],
    tags=["inspections"],
    summary="Inspection history with product/result data (ADMIN / LMO)",
)
def inspection_history(
    status_filter: str | None = Query(None, alias="status", description="PASS / FAIL / REVIEW"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.LMO)),
):
    """Return inspection records joined to analysis/product data for the
    history table.  Optionally filter by compliance result status.

    ADMIN sees all; LMO sees only their own.
    """
    query = (
        db.query(Inspection, Analysis, User)
        .join(Analysis, Inspection.analysis_id == Analysis.id)
        .join(User, Inspection.user_id == User.id)
        .order_by(Inspection.created_at.desc())
    )

    if user.role == UserRole.LMO:
        query = query.filter(Inspection.user_id == user.id)

    # Filter by compliance result (overall_status stored on the Inspection)
    if status_filter:
        sf = status_filter.strip().upper()
        if sf in ("PASS", "FAIL", "REVIEW"):
            query = query.filter(Inspection.overall_status == sf)

    items: list[InspectionHistoryItem] = []
    for insp, analysis, inspector in query.all():
        # Try to get a meaningful product name from extracted fields
        product_name = analysis.category or "Unknown Product"
        commodity_field = (
            db.query(ExtractedField)
            .filter(
                ExtractedField.analysis_id == analysis.id,
                ExtractedField.field_name.in_(["commodity_name", "generic_name"]),
            )
            .first()
        )
        if commodity_field and commodity_field.field_value:
            product_name = commodity_field.field_value
        # Compute compliance score from rule results (lightweight)
        score = None
        if analysis.overall_status:
            from app.compliance.scoring import calculate_score

            rr_rows = (
                db.query(RuleResult)
                .filter(RuleResult.analysis_id == analysis.id)
                .all()
            )
            if rr_rows:
                from dataclasses import dataclass as _dc

                @_dc
                class _RC:
                    rule_number: str = ""
                    title: str = ""
                    category: str = ""
                    severity: str = ""
                    status: str = ""
                    reason: str = ""

                checks = [_RC(status=r.status.value, reason=r.reason or "") for r in rr_rows]
                cs = calculate_score(checks)
                score = cs.total_score

        # Check if a PDF report file exists
        report_available = (
            db.query(Report)
            .filter(Report.analysis_id == analysis.id)
            .first()
        ) is not None
        # Also treat completed analyses as having a report (generated on-demand)
        if not report_available and analysis.status and analysis.status.value == "COMPLETED":
            report_available = True

        items.append(
            InspectionHistoryItem(
                id=insp.id,
                analysis_id=insp.analysis_id,
                product_name=product_name,
                product_category=analysis.category,
                inspector_name=inspector.full_name,
                inspector_id=inspector.id,
                overall_status=insp.overall_status or (analysis.overall_status.value if analysis.overall_status else None),
                compliance_score=round(score, 1) if score is not None else None,
                created_at=insp.created_at,
                report_available=report_available,
            )
        )

    return items


@router.get(
    "/inspections/{inspection_id}",
    response_model=InspectionOut,
    tags=["inspections"],
    summary="Get an inspection by id (ADMIN / LMO)",
)
def get_inspection(
    inspection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.LMO)),
) -> InspectionOut:
    inspection = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if user.role == UserRole.LMO and inspection.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your inspection")
    return InspectionOut.model_validate(inspection)


@router.patch(
    "/inspections/{inspection_id}",
    response_model=InspectionOut,
    tags=["inspections"],
    summary="Update an inspection (ADMIN / owning LMO)",
)
def update_inspection(
    inspection_id: str,
    payload: InspectionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.LMO)),
) -> InspectionOut:
    inspection = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if user.role == UserRole.LMO and inspection.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your inspection")

    if payload.location is not None:
        inspection.location = payload.location
    if payload.observations is not None:
        inspection.observations = payload.observations
    if payload.notes is not None:
        inspection.notes = payload.notes
    if payload.status is not None:
        inspection.status = payload.status

    db.commit()
    db.refresh(inspection)
    return InspectionOut.model_validate(inspection)


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/summary",
    tags=["dashboard"],
    summary="Role-aware dashboard summary (all roles)",
)
def dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return a role-specific summary for the frontend dashboard.

    - ADMIN: user counts, all LMOs, total analyses
    - LMO:   their total inspections + pending, plus all analyses + result counts
    - MANUFACTURER: their products + own analyses
    - RETAILER:     their own analyses
    - CONSUMER:     their own analyses
    """
    from app.models import Product

    role = user.role.value
    total_analyses = db.query(Analysis).count()

    if role == "ADMIN":
        users = db.query(User).all()
        lmos = [
            {"id": u.id, "name": u.full_name, "email": u.email}
            for u in users
            if u.role == UserRole.LMO
        ]
        # Admin result breakdown (from LMO analyses)
        lmo_analyses = (
            db.query(Analysis)
            .join(User, Analysis.user_id == User.id)
            .filter(User.role == UserRole.LMO)
            .all()
        )
        passed = sum(1 for a in lmo_analyses if a.overall_status and a.overall_status.value == "PASS")
        failed = sum(1 for a in lmo_analyses if a.overall_status and a.overall_status.value == "FAIL")
        review = sum(1 for a in lmo_analyses if a.overall_status and a.overall_status.value == "REVIEW")
        return {
            "role": role,
            "stats": {
                "total_users": len(users),
                "total_analyses": total_analyses,
                "admins": sum(1 for u in users if u.role == UserRole.ADMIN),
                "lmos": sum(1 for u in users if u.role == UserRole.LMO),
                "manufacturers": sum(1 for u in users if u.role == UserRole.MANUFACTURER),
                "retailers": sum(1 for u in users if u.role == UserRole.RETAILER),
                "consumers": sum(1 for u in users if u.role == UserRole.CONSUMER),
                "passed": passed,
                "failed": failed,
                "review": review,
            },
            "lmos": lmos,
        }

    if role == "LMO":
        my_inspections = db.query(Inspection).filter(Inspection.user_id == user.id).count()
        pending_inspections = (
            db.query(Inspection)
            .filter(Inspection.user_id == user.id, Inspection.status == InspectionStatus.PENDING)
            .count()
        )
        # Result breakdown from the user's own analyses
        my_analyses = db.query(Analysis).filter(Analysis.user_id == user.id).all()
        passed = sum(1 for a in my_analyses if a.overall_status and a.overall_status.value == "PASS")
        failed = sum(1 for a in my_analyses if a.overall_status and a.overall_status.value == "FAIL")
        review = sum(1 for a in my_analyses if a.overall_status and a.overall_status.value == "REVIEW")
        return {
            "role": role,
            "stats": {
                "my_inspections": my_inspections,
                "pending_inspections": pending_inspections,
                "total_analyses": len(my_analyses),
                "passed": passed,
                "failed": failed,
                "review": review,
            },
        }

    products_count = (
        db.query(Product).filter(Product.created_by == user.id).count()
        if role == "MANUFACTURER"
        else 0
    )
    my_analyses = (
        db.query(Analysis).filter(Analysis.user_id == user.id).count()
    )
    return {
        "role": role,
        "stats": {
            "my_products": products_count,
            "my_analyses": my_analyses,
        },
    }
