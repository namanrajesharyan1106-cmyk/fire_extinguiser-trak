import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.database import SessionLocal
from app.services.asset_service import perform_asset_assignment
from app.models.user import User

db = SessionLocal()

# We need an asset and a location.
from app.models.asset import Asset
from app.models.location import Location

asset = db.query(Asset).first()
location = db.query(Location).first()

if asset and location:
    print(f"Assigning {asset.asset_id} to {location.location_id}")
    try:
        perform_asset_assignment(
            db=db,
            asset_id=asset.asset_id,
            location_id=location.location_id,
            changed_by="test@example.com"
        )
        print("Success")
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("No asset or location found to test")
