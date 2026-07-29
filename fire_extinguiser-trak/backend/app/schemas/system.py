from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PlantBase(BaseModel):
    plant_code: str
    plant_name: str
    address: Optional[str] = None
    contact: Optional[str] = None
    status: Optional[str] = "Active"


class PlantCreate(PlantBase):
    pass


class PlantUpdate(BaseModel):
    plant_name: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    status: Optional[str] = None


class PlantResponse(PlantBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class DepartmentBase(BaseModel):
    dept_code: str
    dept_name: str
    plant_id: Optional[int] = None
    head_name: Optional[str] = None
    status: Optional[str] = "Active"


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    dept_name: Optional[str] = None
    plant_id: Optional[int] = None
    head_name: Optional[str] = None
    status: Optional[str] = None


class DepartmentResponse(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class SystemConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    value: Optional[str] = None
    description: Optional[str] = None


class SystemConfigUpdate(BaseModel):
    value: str


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    related_id: str
    related_type: str
    file_path: str
    file_type: Optional[str] = None
    label: Optional[str] = None
    created_at: datetime


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    message: str
    is_read: bool
    related_id: Optional[str] = None
    related_type: Optional[str] = None
    created_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int] = None
    action: str
    table_name: Optional[str] = None
    record_id: Optional[str] = None
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    ip_address: Optional[str] = None
    device: Optional[str] = None
    browser: Optional[str] = None
    status: Optional[str] = None
    timestamp: datetime


class SearchResult(BaseModel):
    type: str
    id: str
    title: str
    subtitle: Optional[str] = None
    status: Optional[str] = None
    url: Optional[str] = None
