from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from ..core.database import Base
from .asset import Asset, AssetHistory
from .audit import Attachment, AuditLog, Notification
from .auth import PasswordHistory, RefreshToken
from .inspection import Inspection
from .location import Location
from .maintenance import Maintenance
from .role import Permission, Role, role_permissions
from .system import Department, Plant, SystemConfig
from .user import User

__all__ = [
    "Base",
    "Role",
    "Permission",
    "role_permissions",
    "User",
    "RefreshToken",
    "PasswordHistory",
    "Plant",
    "Department",
    "SystemConfig",
    "Location",
    "Asset",
    "AssetHistory",
    "Inspection",
    "Maintenance",
    "AuditLog",
    "Notification",
    "Attachment",
]
