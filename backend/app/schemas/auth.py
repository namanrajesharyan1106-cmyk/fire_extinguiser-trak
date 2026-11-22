from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from .base import APIResponse
from .user import UserResponse


def validate_password(v: str) -> str:
    from ..services.user_service import validate_password_policy
    validate_password_policy(v)
    return v


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
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_revoked: Optional[bool] = False
