"""
Admin router — Plants, Departments, System Config, Audit Logs.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import database
from ..core import dependencies as auth

router = APIRouter()


# ─── Plants ──────────────────────────────────────────────────────────────────
@router.get("/plants", response_model=List[schemas.PlantResponse])
def get_plants(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("manage_plants")),
):
    return db.query(models.Plant).order_by(models.Plant.plant_name).all()


@router.post("/plants", response_model=schemas.PlantResponse, status_code=201)
def create_plant(
    plant: schemas.PlantCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("manage_plants")),
):
    existing = (
        db.query(models.Plant)
        .filter(models.Plant.plant_code == plant.plant_code)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Plant code already exists")

    new_plant = models.Plant(**plant.model_dump())
    db.add(new_plant)
    db.commit()
    db.refresh(new_plant)
    return new_plant


@router.put("/plants/{plant_id}", response_model=schemas.PlantResponse)
def update_plant(
    plant_id: int,
    plant: schemas.PlantUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("manage_plants")),
):
    db_plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not db_plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    for key, value in plant.model_dump(exclude_unset=True).items():
        setattr(db_plant, key, value)
    db.commit()
    db.refresh(db_plant)
    return db_plant


@router.delete("/plants/{plant_id}")
def delete_plant(
    plant_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("manage_plants")),
):
    db_plant = db.query(models.Plant).filter(models.Plant.id == plant_id).first()
    if not db_plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    db.delete(db_plant)
    db.commit()
    return {"message": "Plant deleted"}


# ─── Departments ─────────────────────────────────────────────────────────────
@router.get("/departments", response_model=List[schemas.DepartmentResponse])
def get_departments(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("manage_departments")),
):
    return db.query(models.Department).order_by(models.Department.dept_name).all()


@router.post("/departments", response_model=schemas.DepartmentResponse, status_code=201)
def create_department(
    dept: schemas.DepartmentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("manage_departments")),
):
    existing = (
        db.query(models.Department)
        .filter(models.Department.dept_code == dept.dept_code)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Department code already exists")
    new_dept = models.Department(**dept.model_dump())
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    return new_dept


@router.put("/departments/{dept_id}", response_model=schemas.DepartmentResponse)
def update_department(
    dept_id: int,
    dept: schemas.DepartmentUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("manage_departments")),
):
    db_dept = (
        db.query(models.Department).filter(models.Department.id == dept_id).first()
    )
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    for key, value in dept.model_dump(exclude_unset=True).items():
        setattr(db_dept, key, value)
    db.commit()
    db.refresh(db_dept)
    return db_dept


@router.delete("/departments/{dept_id}")
def delete_department(
    dept_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("manage_departments")),
):
    db_dept = (
        db.query(models.Department).filter(models.Department.id == dept_id).first()
    )
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    db.delete(db_dept)
    db.commit()
    return {"message": "Department deleted"}


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
