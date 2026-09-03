"""Authentication endpoints: register, login, me, zones, and admin user management.

Phase 6 — Authentication + RBAC.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserRole, Zone
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    UserUpdateRequest,
    ZoneOut,
)

router = APIRouter()


@router.post(
    "/auth/register",
    status_code=201,
    response_model=UserOut,
    tags=["auth"],
    summary="Register a new user (default role CONSUMER)",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserOut:
    """Create a new user account.

    Public self-service registration is allowed for CONSUMER, RETAILER,
    MANUFACTURER and LMO. The ADMIN role is reserved and can only be
    assigned by an existing administrator.
    """
    exists = db.query(User).filter(User.email == payload.email.lower()).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")

    role = payload.role
    if role == UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="The ADMIN role must be assigned by an administrator",
        )

    # LMOs must register in a zone (their jurisdiction).
    zone_id = payload.zone_id
    if role == UserRole.LMO:
        if not zone_id:
            raise HTTPException(
                status_code=422,
                detail="An LMO must select a zone during registration",
            )
        if db.get(Zone, zone_id) is None:
            raise HTTPException(status_code=404, detail="Zone not found")
    else:
        zone_id = None

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=role,
        zone_id=zone_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["auth"],
    summary="Log in with email and password",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Validate credentials and return a JWT access token."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get(
    "/auth/me",
    response_model=UserOut,
    tags=["auth"],
    summary="Get the current authenticated user",
)
def me(
    user: User = Depends(get_current_user),
) -> UserOut:
    """Return the profile of the currently authenticated user."""
    return UserOut.model_validate(user)


# --- Zone management (ADMIN only) -------------------------------------------


@router.get(
    "/zones/public",
    response_model=list[ZoneOut],
    tags=["auth"],
    summary="List zones for LMO registration (public)",
)
def list_zones_public(
    db: Session = Depends(get_db),
) -> list[ZoneOut]:
    """Return all zones (id + name) so an LMO can register in a zone.

    Only exposes zone identity needed for registration, not privileged data.
    """
    zones = db.query(Zone).order_by(Zone.name).all()
    return [ZoneOut.model_validate(z) for z in zones]


@router.post(
    "/zones",
    response_model=ZoneOut,
    status_code=201,
    tags=["admin"],
    summary="Create a zone (ADMIN only)",
)
def create_zone(
    name: str,
    jurisdiction: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> ZoneOut:
    """Create a new geographic/administrative zone."""
    exists = db.query(Zone).filter(Zone.name == name).first()
    if exists:
        raise HTTPException(status_code=409, detail="Zone already exists")
    zone = Zone(name=name, jurisdiction=jurisdiction)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return ZoneOut.model_validate(zone)


@router.get(
    "/zones",
    response_model=list[ZoneOut],
    tags=["admin"],
    summary="List all zones (ADMIN only)",
)
def list_zones(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[ZoneOut]:
    """Return every zone in the system."""
    zones = db.query(Zone).all()
    return [ZoneOut.model_validate(z) for z in zones]


# --- Admin user management ---------------------------------------------------


@router.get(
    "/users",
    response_model=list[UserOut],
    tags=["admin"],
    summary="List all users (ADMIN only)",
)
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[UserOut]:
    """Return all users with their roles and assigned zones."""
    users = db.query(User).all()
    return [UserOut.model_validate(u) for u in users]


@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    tags=["admin"],
    summary="Update a user's role / status / zone (ADMIN only)",
)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> UserOut:
    """Update role, active status, or zone assignment for a user."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role is not None:
        user.role = payload.role
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.zone_id is not None:
        # Allow LMO users to be assigned to a zone; validate the zone exists
        zone = db.get(Zone, payload.zone_id)
        if zone is None:
            raise HTTPException(status_code=404, detail="Zone not found")
        user.zone_id = payload.zone_id
    elif payload.zone_id is not None or "zone_id" in payload.model_dump(exclude_unset=True):
        if payload.zone_id is None:
            user.zone_id = None

    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get(
    "/admins/lmos",
    response_model=list[UserOut],
    tags=["admin"],
    summary="List LMOs grouped by zone (ADMIN only)",
)
def list_lmos_by_zone(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[UserOut]:
    """Return all LMOs with their zone assignments.

    Used by the ADMIN dashboard to see each Legal Metrology Officer and the
    zone (jurisdiction) they serve.
    """
    lmos = (
        db.query(User)
        .filter(User.role == UserRole.LMO)
        .order_by(User.zone_id)
        .all()
    )
    return [UserOut.model_validate(u) for u in lmos]
