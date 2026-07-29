from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
import logging
from fastapi import Request

from .database import get_db
from .security import decode_token

# Note: Since models are not yet refactored to app/models/, we import from the existing structure.
# We'll need to update this once models are split.
# To prevent circular imports and allow smooth migration, we might need to rely on the service layer.

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user_dependency():
    """
    Dependency factory to avoid circular imports during migration.
    We will lazy load the UserService.
    """

    def _get_current_user(
        token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
    ):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = decode_token(token)
            user_id_str: str = payload.get("sub")
            token_type: str = payload.get("type", "access")

            if user_id_str is None or token_type != "access":
                raise credentials_exception

        except JWTError:
            raise credentials_exception

        # Lazy import to avoid circular dependencies
        from ..services.user_service import (
            check_account_status,
            get_user_by_id_or_email,
        )

        user = get_user_by_id_or_email(db, user_id_str)

        if user is None:
            raise credentials_exception

        # Security checks: Active, not locked out
        check_account_status(user)

        return user

    return _get_current_user


get_current_user = get_current_user_dependency()


logger = logging.getLogger(__name__)

def require_permission(permission: str):
    """
    Returns a FastAPI dependency that checks if the current user has
    the specified permission based on their role stored in DB.
    """

    def checker(request: Request, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
        from ..services.rbac_service import role_has_permission, get_role_permissions

        if not role_has_permission(db, current_user.role, permission):
            current_permissions = get_role_permissions(db, current_user.role)
            logger.warning(
                f"Authorization Denied | Endpoint: {request.url.path} | "
                f"Current User ID: {current_user.id} | Employee ID: {current_user.employee_id} | "
                f"Current Role: {current_user.role} | Permissions: {current_permissions} | "
                f"Required Permission: {permission} | Reason for denial: User role lacks required permission."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. You do not have the required access.",
            )
        return current_user

    return checker


def require_roles(allowed_roles: List[str]):
    """
    Returns a FastAPI dependency that checks if the current user has one of the allowed roles.
    """

    def checker(request: Request, current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Authorization Denied | Endpoint: {request.url.path} | "
                f"Current User ID: {current_user.id} | Employee ID: {current_user.employee_id} | "
                f"Current Role: {current_user.role} | Required Roles: {allowed_roles} | "
                f"Reason for denial: User role is not in the allowed roles."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access restricted. You do not have the required role.",
            )
        return current_user

    return checker
