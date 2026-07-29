from typing import Optional

from sqlalchemy.orm import Session

from ..models.location import Location
from ..schemas.location import LocationCreate, LocationUpdate
from .base_repository import BaseRepository


class LocationRepository(BaseRepository[Location, LocationCreate, LocationUpdate]):
    # Note: Location primary key is string (location_id)
    def get(self, db: Session, id: str) -> Optional[Location]:
        return db.query(Location).filter(Location.location_id == id).first()

    def get_by_qr(self, db: Session, *, qr_code: str) -> Optional[Location]:
        return db.query(Location).filter(Location.qr_code == qr_code).first()

    def remove(self, db: Session, *, id: str) -> Location:
        obj = self.get(db, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


location_repo = LocationRepository(Location)
