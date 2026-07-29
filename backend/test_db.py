import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.database import SessionLocal
from app.routers.locations import create_location
from app.schemas.location import LocationCreate
from app.models.user import User

db = SessionLocal()
user = db.query(User).first()

loc = LocationCreate(
    location_name="Test Direct Location",
    plant="PP02",
    area="Assembly",
    department="Production",
    building="Main Building",
    floor="Ground",
    required_asset_type_id=1,
    required_capacity_id=1
)

try:
    create_location(location=loc, db=db, current_user=user)
except Exception as e:
    import traceback
    traceback.print_exc()
