from datetime import datetime
from typing import Optional


from pydantic import BaseModel, ConfigDict, field_validator
import re

def validate_password(v: str) -> str:
    from ..services.user_service import validate_password_policy
    validate_password_policy(v)
    return v

from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    SAFETY_HEAD = "SAFETY HEAD"
    SAFETY_OFFICER = "SAFETY OFFICER"
    INSPECTOR = "INSPECTOR"
    MAINTENANCE = "MAINTENANCE"
    VIEWER = "VIEWER"
    IT_ADMIN = "IT ADMIN"
class UserBase(BaseModel):
    employee_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[str] = "Active"
    phone: Optional[str] = None
    plant: Optional[str] = None


class UserCreate(UserBase):
    role: UserRole
    password: str

    @field_validator("password")
    def check_password(cls, v):
        return validate_password(v)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[str] = None
    phone: Optional[str] = None
    plant: Optional[str] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_first_login: Optional[bool] = True
    last_login: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    last_login_device: Optional[str] = None
    failed_login_attempts: Optional[int] = 0
    locked_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
