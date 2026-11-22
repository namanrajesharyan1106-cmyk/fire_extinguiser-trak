from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def test_maintenance_submission():
    print("1. Logging in...")
    response = client.post(
        "/api/auth/login",
        data={"username": "admin@fireext.com", "password": "change_me_immediately_123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token_data = response.json()["data"]
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("2. Submitting maintenance ticket...")
    from app.core.database import SessionLocal
    from app.models import Asset, Location
    db = SessionLocal()
    try:
        asset = db.query(Asset).first()
        loc = db.query(Location).first()
        asset_id = asset.asset_id if asset else "AST-TEST"
        location_id = loc.location_id if loc else "LOC-TEST"
    finally:
        db.close()

    maint_resp = client.post(
        "/api/maintenance",
        headers=headers,
        json={
            "asset_id": asset_id,
            "location_id": location_id,
            "issue": "Test issue",
            "priority": "Medium",
            "source": "Manual"
        }
    )
    print(f"Status Code: {maint_resp.status_code}")
    print(f"Response: {maint_resp.text}")
    assert maint_resp.status_code == 201, f"Maintenance creation failed: {maint_resp.text}"

if __name__ == "__main__":
    try:
        test_maintenance_submission()
        print("\nTest passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import sys
        sys.exit(1)
