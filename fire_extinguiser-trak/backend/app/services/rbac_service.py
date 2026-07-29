from sqlalchemy.orm import Session

from ..models import Role


def role_has_permission(db: Session, role_name: str, permission_name: str) -> bool:
    """
    Check if a given role name has the specified permission.
    If the database check fails, it acts securely (returns False).
    """
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        return False

    for p in role.permissions:
        if p.name == permission_name:
            return True

    return False


def get_role_permissions(db: Session, role_name: str):
    """Return a list of permission names for a role."""
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        return []
    return [p.name for p in role.permissions]
