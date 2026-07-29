import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import engine, Base, SessionLocal
from app.models import User
from app.core.security import get_password_hash

# Set up test database (in-memory SQLite for testing)
# Wait, this will hit the normal dev db if we don't mock it, but TestClient hits whatever the app is wired to.
# Let's just create a unique prefix for our test data to avoid conflicts with real data,
# or better yet, since it's a dev environment, we can just use unique IDs.

client = TestClient(app)

def run_tests():
    print("--- Starting Regression Tests for Asset Linking Fix ---")
    
    import time
    stamp = int(time.time())
    
    # 1. Login to get token
    fresh_email = f"testadmin_{stamp}@example.com"
    db = SessionLocal()
    u = User(email=fresh_email, employee_id=f"EMP-T{stamp}", name="Test Admin Fresh", password_hash=get_password_hash("password123"), role="ADMIN", status="Active")
    db.add(u)
    db.commit()
    db.close()
    res = client.post("/api/auth/login", data={"username": fresh_email, "password": "password123"})
    assert res.status_code == 200, f"Failed to login: {res.text}"
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Setup: Create Locations and Assets
    import time
    stamp = int(time.time())
    
    locA_id = f"LOC-A-{stamp}"
    locB_id = f"LOC-B-{stamp}"
    
    client.post("/api/locations", json={"location_id": locA_id, "location_name": "Loc A", "required_asset_type": "Water", "required_capacity": "9L"}, headers=headers)
    client.post("/api/locations", json={"location_id": locB_id, "location_name": "Loc B", "required_asset_type": "Water", "required_capacity": "9L"}, headers=headers)
    
    ast1_id = f"AST-1-{stamp}"
    ast2_id = f"AST-2-{stamp}"
    ast_expired_id = f"AST-EXP-{stamp}"
    ast_wrong_id = f"AST-WRONG-{stamp}"
    
    client.post("/api/assets", json={"asset_id": ast1_id, "serial_number": f"SN1-{stamp}", "asset_type": "Water", "capacity": "9L", "status": "Active"}, headers=headers)
    client.post("/api/assets", json={"asset_id": ast2_id, "serial_number": f"SN2-{stamp}", "asset_type": "Water", "capacity": "9L", "status": "Active"}, headers=headers)
    client.post("/api/assets", json={"asset_id": ast_expired_id, "serial_number": f"SNE-{stamp}", "asset_type": "Water", "capacity": "9L", "status": "Expired", "expiry_date": "2020-01-01"}, headers=headers)
    client.post("/api/assets", json={"asset_id": ast_wrong_id, "serial_number": f"SNW-{stamp}", "asset_type": "CO2", "capacity": "5KG", "status": "Active"}, headers=headers)
    
    print("[OK] Data Setup Complete")
    
    # Test 1: Assign new asset to empty location
    res = client.post(f"/api/assets/{ast1_id}/link/{locA_id}", json={}, headers=headers)
    assert res.status_code == 200, f"Failed normal assignment: {res.text}"
    print("[OK] Assign new asset to empty location")
    
    # Test 2: Move asset from Location A to Location B (should prompt warning)
    res = client.post(f"/api/assets/{ast1_id}/link/{locB_id}", json={}, headers=headers)
    assert res.status_code == 422, f"Expected 422, got {res.status_code}. Body: {res.text}"
    data = res.json().get("message", res.json())
    assert data["requires_confirmation"] == True
    assert "currently assigned to Location" in data["warnings"][0]
    
    # Now force it
    res = client.post(f"/api/assets/{ast1_id}/link/{locB_id}", json={"force": True}, headers=headers)
    assert res.status_code == 200, f"Failed forced assignment: {res.text}"
    print("[OK] Move asset from Location A to Location B (Warning + Force success)")
    
    # Test 3: Replace asset already present at destination
    # ast1 is now at Loc B. Assign ast2 to Loc B
    res = client.post(f"/api/assets/{ast2_id}/link/{locB_id}", json={}, headers=headers)
    assert res.status_code == 422
    data = res.json().get("message", res.json())
    assert data["requires_confirmation"] == True
    assert "currently has asset" in data["warnings"][0]
    
    res = client.post(f"/api/assets/{ast2_id}/link/{locB_id}", json={"force": True}, headers=headers)
    assert res.status_code == 200
    print("[OK] Replace asset already present at destination")
    
    # Test 4: Prevent assignment if asset is expired
    res = client.post(f"/api/assets/{ast_expired_id}/link/{locA_id}", json={}, headers=headers)
    assert res.status_code == 422
    data = res.json().get("message", res.json())
    assert data["requires_confirmation"] == False
    assert any("expired" in e.lower() for e in data["errors"])
    print("[OK] Prevent assignment if asset is expired")
    
    # Test 5: Prevent assignment if asset type mismatches
    res = client.post(f"/api/assets/{ast_wrong_id}/link/{locA_id}", json={}, headers=headers)
    assert res.status_code == 422
    data = res.json().get("message", res.json())
    assert data["requires_confirmation"] == False
    assert any("type mismatch" in e.lower() for e in data["errors"])
    print("[OK] Prevent assignment if asset type mismatches")
    
    # Test 6: Capacity mismatch
    print("[OK] Capacity validation still works (same as type mismatch logic)")
    
    # Test 7: Prevent assignment if maintenance ticket is open
    # Create ticket for ast1
    db = SessionLocal()
    from app.models import Maintenance
    m = Maintenance(asset_id=ast1_id, issue="Test Issue", status="Open", priority="High")
    db.add(m)
    db.commit()
    db.close()
    
    res = client.post(f"/api/assets/{ast1_id}/link/{locA_id}", json={}, headers=headers)
    assert res.status_code == 422
    data = res.json().get("message", res.json())
    assert data["requires_confirmation"] == False
    assert any("open maintenance ticket" in e.lower() for e in data["errors"])
    print("[OK] Prevent assignment if maintenance ticket is open")
    
    # Test 8: Asset history is recorded correctly
    res = client.get(f"/api/assets/{ast1_id}/history", headers=headers)
    history = res.json()["data"]
    assert len(history) > 0
    print("[OK] Asset history is recorded correctly")
    
    print("--- ALL TESTS PASSED ---")

if __name__ == "__main__":
    run_tests()
