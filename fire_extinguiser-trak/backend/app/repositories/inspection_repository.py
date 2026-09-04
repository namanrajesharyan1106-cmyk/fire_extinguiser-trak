from sqlalchemy.orm import Session

from ..models.inspection import Inspection
from ..schemas.inspection import InspectionCreate
from .base_repository import BaseRepository


class InspectionRepository(
    BaseRepository[Inspection, InspectionCreate, InspectionCreate]
):
    def get_by_location(self, db: Session, *, location_id: str):
        return db.query(Inspection).filter(Inspection.location_id == location_id).all()

    def get_by_asset(self, db: Session, *, asset_id: str):
        return db.query(Inspection).filter(Inspection.asset_id == asset_id).all()


inspection_repo = InspectionRepository(Inspection)
