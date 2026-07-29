from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MaintenanceBase(BaseModel):
    asset_id: Optional[str] = None
    location_id: Optional[str] = None
    issue: Optional[str] = None
    priority: Optional[str] = "Medium"
    assigned_to: Optional[str] = None
    remarks: Optional[str] = None
    source: Optional[str] = "Manual"


class MaintenanceCreate(MaintenanceBase):
    pass


class MaintenanceUpdate(BaseModel):
    issue: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    technician_id: Optional[int] = None
    remarks: Optional[str] = None


class MaintenanceStatusUpdate(BaseModel):
    new_status: str
    remarks: Optional[str] = None
    technician_id: Optional[int] = None
    verified_by: Optional[str] = None


class MaintenanceResponse(MaintenanceBase):
    model_config = ConfigDict(from_attributes=True)
    maintenance_id: int
    status: str
    technician_id: Optional[int] = None
    verified_by: Optional[str] = None
    opened_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    closed_date: Optional[datetime] = None
    inspection_id: Optional[int] = None
    created_at: Optional[datetime] = None
