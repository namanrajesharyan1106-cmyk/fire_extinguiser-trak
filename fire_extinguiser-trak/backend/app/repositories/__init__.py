from .asset_repository import asset_repo
from .inspection_repository import inspection_repo
from .location_repository import location_repo
from .maintenance_repository import maintenance_repo
from .user_repository import user_repo

__all__ = [
    "user_repo",
    "location_repo",
    "asset_repo",
    "inspection_repo",
    "maintenance_repo",
]
