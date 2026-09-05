"""FastAPI dependency helpers for authentication and authorization.

Central place for:
- get_current_user: resolve a bearer token to a User (returns 401 if invalid)
- require_roles: role guard dependency factory (returns 403 if role mismatch)

These dependencies are role-based and inherited by all protected endpoints.
The compliance engine itself never consults roles — access control lives here.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, UserRole

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from the bearer token.

    Raises 401 if the token is missing, invalid, expired, or the user is
    not found or deactivated.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return user


def require_roles(*roles: UserRole | str):
    """Return a dependency that only allows the given roles.

    Usage:
        @router.get("/x")
        def x(user: User = Depends(require_roles(UserRole.ADMIN))):
            ...
    """
    allowed = {r.value if isinstance(r, UserRole) else r for r in roles}

    def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role.value} is not permitted for this action",
            )
        return user

    return _guard


def get_current_lmo(
    user: User = Depends(get_current_user),
) -> User:
    """Shortcut dependency requiring an LMO role."""
    if user.role != UserRole.LMO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Legal Metrology Officers can perform this action",
        )
    return user
