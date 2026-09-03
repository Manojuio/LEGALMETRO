"""Authentication endpoints: register, login, me, and admin user management.

Phase 6 — Authentication + RBAC.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    UserUpdateRequest,
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

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=role,
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
    if user is None or not verify_password(user.hashed_password, payload.hashed_password):
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
    """Return all users with their roles."""
    users = db.query(User).all()
    return [UserOut.model_validate(u) for u in users]


@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    tags=["admin"],
    summary="Update a user's role / status (ADMIN only)",
)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> UserOut:
    """Update role, active status, or display name for a user."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role is not None:
        user.role = payload.role
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get(
    "/admins/lmos",
    response_model=list[UserOut],
    tags=["admin"],
    summary="List all LMOs (ADMIN only)",
)
def list_lmos(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[UserOut]:
    """Return every Legal Metrology Officer (LMO) in the system.

    The ADMIN oversees all LMOs and can review / download their reports.
    """
    lmos = (
        db.query(User)
        .filter(User.role == UserRole.LMO)
        .order_by(User.full_name)
        .all()
    )
    return [UserOut.model_validate(u) for u in lmos]
