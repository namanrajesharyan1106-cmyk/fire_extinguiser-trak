from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class InspectionBase(BaseModel):
    location_id: str
    asset_id: Optional[str] = None
    inspector: Optional[str] = None
    pressure: Optional[str] = None
    seal: Optional[str] = None
    pin: Optional[str] = None
    gauge: Optional[str] = None
    hose: Optional[str] = None
    nozzle: Optional[str] = None
    visibility: Optional[str] = None
    accessibility: Optional[str] = None
    mounting: Optional[str] = None
    safety_tag: Optional[str] = None
    cylinder_damage: Optional[str] = None
    remarks: Optional[str] = None


class InspectionCreate(InspectionBase):
    pass


class InspectionResponse(InspectionBase):
    model_config = ConfigDict(from_attributes=True)
    inspection_id: int
    inspection_no: Optional[str] = None
    overall_status: Optional[str] = None
    inspection_date: Optional[datetime] = None
    photo: Optional[str] = None
    created_at: Optional[datetime] = None
