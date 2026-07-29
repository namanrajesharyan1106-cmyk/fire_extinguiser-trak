from datetime import datetime
from typing import Optional


from pydantic import BaseModel, ConfigDict, field_validator
import re

def validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[@$!%*?&#]", v):
        raise ValueError("Password must contain at least one special character")
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
    role: Optional[str] = None
    status: Optional[str] = "Active"
    phone: Optional[str] = None
    plant: Optional[str] = None


class UserCreate(UserBase):
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
