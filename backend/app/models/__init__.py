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
from .system import (
    MasterPlant, MasterDepartment, SequenceTracker, SystemConfig,
    MasterArea, MasterBuilding, MasterFloor, 
    MasterAssetType, MasterCapacityType, 
    MasterRiskCategory, MasterInspectionFrequency
)
from .user import User, UserPlant

__all__ = [
    "Base",
    "Role",
    "Permission",
    "role_permissions",
    "User",
    "UserPlant",
    "RefreshToken",
    "PasswordHistory",
    "MasterPlant",
    "MasterDepartment",
    "SequenceTracker",
    "SystemConfig",
    "Location",
    "Asset",
    "AssetHistory",
    "Inspection",
    "Maintenance",
    "AuditLog",
    "Notification",
    "Attachment",
    "MasterArea",
    "MasterBuilding",
    "MasterFloor",
    "MasterAssetType",
    "MasterCapacityType",
    "MasterRiskCategory",
    "MasterInspectionFrequency",
]
