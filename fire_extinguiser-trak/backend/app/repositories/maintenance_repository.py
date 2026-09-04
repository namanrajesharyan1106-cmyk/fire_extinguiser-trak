from sqlalchemy.orm import Session

from ..models.maintenance import Maintenance
from ..schemas.maintenance import MaintenanceCreate, MaintenanceUpdate
from .base_repository import BaseRepository


class MaintenanceRepository(
    BaseRepository[Maintenance, MaintenanceCreate, MaintenanceUpdate]
):
    def get_by_asset(self, db: Session, *, asset_id: str):
        return db.query(Maintenance).filter(Maintenance.asset_id == asset_id).all()

    def get_by_location(self, db: Session, *, location_id: str):
        return (
            db.query(Maintenance).filter(Maintenance.location_id == location_id).all()
        )

    def get_by_status(self, db: Session, *, status: str):
        return db.query(Maintenance).filter(Maintenance.status == status).all()


maintenance_repo = MaintenanceRepository(Maintenance)
