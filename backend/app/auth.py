"""
Authentication utilities (Duplicate logic removed)
"""

from sqlalchemy.orm import Session

from . import models
from .core.config import settings
from .core.constants import PERMISSIONS, ROLES
from .core.logger import logger


# Duplicate authentication logic removed to avoid conflict.
# Use app/core/dependencies.py for get_current_user, require_permission, and require_roles.
def _seed_roles_and_permissions(db: Session):
    """Seeds the DB with Roles and Permissions from constants if empty."""
    # Check if roles exist
    if db.query(models.Role).first():
        return

    logger.info("[STARTUP] Seeding Roles and Permissions...")

    role_objects = {}
    for r_name in ROLES:
        r = models.Role(name=r_name)
        db.add(r)
        role_objects[r_name] = r

    db.commit()

    for p_name, allowed_roles in PERMISSIONS.items():
        p = models.Permission(name=p_name)
        db.add(p)
        for r_name in allowed_roles:
            if r_name in role_objects:
                role_objects[r_name].permissions.append(p)

    db.commit()
    logger.info("[STARTUP] Seeded Roles and Permissions successfully.")


def create_default_admin(db: Session) -> None:
    """
    Called at application startup.
    Seeds roles/permissions and creates the default ADMIN user if no ADMIN exists.
    """
    _seed_roles_and_permissions(db)

    existing_admin = db.query(models.User).filter(models.User.role == "ADMIN").first()

    if existing_admin:
        return  # At least one admin exists

    existing_email = (
        db.query(models.User)
        .filter(models.User.email == settings.DEFAULT_ADMIN_EMAIL)
        .first()
    )

    if existing_email:
        # Upgrade existing user to ADMIN
        existing_email.role = "ADMIN"
        existing_email.is_first_login = False
        existing_email.status = "Active"
        existing_email.locked_until = None
        existing_email.failed_login_attempts = 0
        db.commit()
        logger.info(
            f"[STARTUP] Upgraded existing user {settings.DEFAULT_ADMIN_EMAIL} to ADMIN"
        )
        return

    from .core.security import get_password_hash

    admin_user = models.User(
        employee_id=settings.DEFAULT_ADMIN_EMPLOYEE_ID,
        name=settings.DEFAULT_ADMIN_NAME,
        email=settings.DEFAULT_ADMIN_EMAIL,
        password_hash=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
        department=settings.DEFAULT_ADMIN_DEPARTMENT,
        role=settings.DEFAULT_ADMIN_ROLE,
        status="Active",
        is_first_login=False,
        plant=settings.DEFAULT_ADMIN_PLANT,
    )
    db.add(admin_user)
    db.commit()
    logger.info(f"[STARTUP] Default admin created: {settings.DEFAULT_ADMIN_EMAIL}")
