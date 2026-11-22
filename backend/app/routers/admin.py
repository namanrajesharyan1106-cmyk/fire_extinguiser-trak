"""
Admin router — Plants, Departments, System Config, Audit Logs.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import database
from ..core import dependencies as auth

router = APIRouter()




# ─── System Config ────────────────────────────────────────────────────────────
@router.get("/config", response_model=List[schemas.SystemConfigResponse])
def get_system_configs(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(
        auth.require_permission("manage_system_config")
    ),
):
    return db.query(models.SystemConfig).order_by(models.SystemConfig.key).all()


@router.put("/config/{key}")
def update_system_config(
    key: str,
    payload: schemas.SystemConfigUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(
        auth.require_permission("manage_system_config")
    ),
):
    config = (
        db.query(models.SystemConfig).filter(models.SystemConfig.key == key).first()
    )
    if not config:
        config = models.SystemConfig(key=key, value=payload.value)
        db.add(config)
    else:
        config.value = payload.value
    db.commit()
    return {"message": f"Config '{key}' updated", "value": payload.value}


# ─── Audit Logs ───────────────────────────────────────────────────────────────
@router.get("/audit-logs", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    table_name: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_audit_logs")),
):
    query = db.query(models.AuditLog)
    if table_name:
        query = query.filter(models.AuditLog.table_name == table_name)
    if action:
        query = query.filter(models.AuditLog.action == action)
    return (
        query.order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    )


# ─── Constants (for frontend dropdowns) ──────────────────────────────────────
@router.get("/constants")
def get_constants(current_user: models.User = Depends(auth.get_current_user)):
    from ..core.constants import (
        ASSET_STATUSES,
        ASSET_TYPES,
        ATTACHMENT_LABELS,
        CHECKLIST_VALUES,
        LOCATION_STATUSES,
        MAINTENANCE_PRIORITIES,
        MAINTENANCE_STATUSES,
        MOVEMENT_TYPES,
        RISK_CATEGORIES,
        ROLES,
    )

    return {
        "roles": ROLES,
        "asset_types": ASSET_TYPES,
        "asset_statuses": ASSET_STATUSES,
        "location_statuses": LOCATION_STATUSES,
        "risk_categories": RISK_CATEGORIES,
        "maintenance_statuses": MAINTENANCE_STATUSES,
        "maintenance_priorities": MAINTENANCE_PRIORITIES,
        "movement_types": MOVEMENT_TYPES,
        "attachment_labels": ATTACHMENT_LABELS,
        "checklist_values": CHECKLIST_VALUES,
    }
