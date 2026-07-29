import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.database import SessionLocal
from app.routers.assets import get_compatible_locations
from app.models.asset import Asset
from app.models.user import User
import json

db = SessionLocal()

asset = db.query(Asset).first()
if asset:
    print(f"Testing compatibility for Asset ID: {asset.asset_id}")
    
    try:
        user = User(email="test@example.com")
        res = get_compatible_locations(asset_id=asset.asset_id, db=db, current_user=user)
        print("Success!")
        data = res["data"]
        print(f"Compatible Locations: {len(data['compatible'])}")
        print(f"Rejected Locations: {len(data['rejected'])}")
        if len(data['rejected']) > 0:
            print("Sample rejection:")
            print(data['rejected'][0]['location_id'], data['rejected'][0]['rejection_reasons'])
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("No asset found")
