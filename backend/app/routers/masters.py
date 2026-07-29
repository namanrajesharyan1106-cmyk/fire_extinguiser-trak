"""
Master Data Management Router
"""

from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .. import models
from ..core import database
from ..core import dependencies as auth
from ..schemas.base import APIResponse

router = APIRouter()

# Schema for new Masters
class MasterCreateUpdate(BaseModel):
    name: str

class MasterResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    
class GenericMasterResponse(BaseModel):
    id: int
    name: str
    status: str

# Helper to map master type to model class
MASTER_MODELS = {
    "plants": models.MasterPlant,
    "departments": models.MasterDepartment,
    "areas": models.MasterArea,
    "buildings": models.MasterBuilding,
    "floors": models.MasterFloor,
    "asset_types": models.MasterAssetType,
    "capacity_types": models.MasterCapacityType,
    "risk_categories": models.MasterRiskCategory,
    "inspection_frequencies": models.MasterInspectionFrequency,
}

@router.get("/active")
def get_active_masters(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Fetch all active master data for dropdowns."""
    data = {}
    # Fetch active records for all master models
    for key, model_cls in MASTER_MODELS.items():
        records = db.query(model_cls).filter(model_cls.is_active == True).order_by(model_cls.name).all()
        data[key] = [{"id": r.id, "name": r.name} for r in records]
        
    return {"success": True, "message": "Master data retrieved", "data": data, "errors": None}


# Admin CRUD Endpoints
@router.get("/admin/{master_type}")
def get_admin_masters(master_type: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_roles(["ADMIN"]))):
        
    model_cls = MASTER_MODELS.get(master_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Master type not found")
        
    records = db.query(model_cls).order_by(model_cls.name).all()
    return {"success": True, "data": [{"id": r.id, "name": r.name, "is_active": r.is_active} for r in records]}


@router.post("/admin/{master_type}")
def create_master(master_type: str, payload: MasterCreateUpdate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_roles(["ADMIN"]))):
        
    model_cls = MASTER_MODELS.get(master_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Master type not found")
        
    existing = db.query(model_cls).filter(model_cls.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Name already exists")
        
    new_record = model_cls(name=payload.name, is_active=True)
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return {"success": True, "data": {"id": new_record.id, "name": new_record.name, "is_active": new_record.is_active}}


@router.put("/admin/{master_type}/{id}")
def update_master(master_type: str, id: int, payload: MasterCreateUpdate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_roles(["ADMIN"]))):
        
    model_cls = MASTER_MODELS.get(master_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Master type not found")
        
    record = db.query(model_cls).filter(model_cls.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    existing = db.query(model_cls).filter(model_cls.name == payload.name, model_cls.id != id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Name already exists")
        
    record.name = payload.name
    db.commit()
    db.refresh(record)
    return {"success": True, "data": {"id": record.id, "name": record.name, "is_active": record.is_active}}


@router.put("/admin/{master_type}/{id}/toggle-status")
def toggle_master_status(master_type: str, id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_roles(["ADMIN"]))):
        
    model_cls = MASTER_MODELS.get(master_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Master type not found")
        
    record = db.query(model_cls).filter(model_cls.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    record.is_active = not record.is_active
    db.commit()
    return {"success": True, "data": {"id": record.id, "is_active": record.is_active}}
