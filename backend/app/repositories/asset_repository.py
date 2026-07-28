from typing import Optional

from sqlalchemy.orm import Session

from ..models.asset import Asset
from ..schemas.asset import AssetCreate, AssetUpdate
from .base_repository import BaseRepository


class AssetRepository(BaseRepository[Asset, AssetCreate, AssetUpdate]):
    def get(self, db: Session, id: str) -> Optional[Asset]:
        return db.query(Asset).filter(Asset.asset_id == id).first()

    def get_by_serial(self, db: Session, *, serial_number: str) -> Optional[Asset]:
        return db.query(Asset).filter(Asset.serial_number == serial_number).first()

    def get_by_location(self, db: Session, *, location_id: str) -> Optional[Asset]:
        return db.query(Asset).filter(Asset.location_id == location_id).first()

    def remove(self, db: Session, *, id: str) -> Asset:
        obj = self.get(db, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


asset_repo = AssetRepository(Asset)
