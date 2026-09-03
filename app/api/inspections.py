"""Inspection workflow endpoints (Phase 18).

An Inspection attaches an LMO field inspection (location, observations,
status) to an existing analysis. Only ADMIN and LMO can create/manage
inspections, per the roles matrix.

Also exposes a dashboard summary endpoint used by the LMO / ADMIN dashboards.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Analysis, Inspection, InspectionStatus, RuleResult, User, UserRole

router = APIRouter()


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
    observations: str | None
    notes: str | None
    created_at: object | None = None


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
    - LMO:   their total inspections + pending, plus all analyses
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
        return {
            "role": role,
            "stats": {
                "my_inspections": my_inspections,
                "pending_inspections": pending_inspections,
                "total_analyses": total_analyses,
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
