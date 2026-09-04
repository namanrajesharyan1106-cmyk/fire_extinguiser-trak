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


from .base import APIResponse
from .user import UserResponse


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


class LoginResponse(APIResponse[Token]):
    access_token: str
    token_type: str


class TokenRefresh(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    def check_password(cls, v):
        return validate_password(v)


class ResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    def check_password(cls, v):
        return validate_password(v)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    is_revoked: bool
