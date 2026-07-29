import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def login_as(email, password="change_me_immediately_123"):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_scenario_1_asset_lifecycle():
    print("--- Running Scenario 1: Asset Lifecycle ---")
    admin_token = login_as("admin@fireext.com")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Create Location
    loc_id = f"UAT-LOC-{int(time.time())}"
    res = client.post("/api/locations", json={
        "location_id": loc_id,
        "location_name": f"UAT Test Room {loc_id}",
        "plant": "Head Office",
        "department": "Safety",
        "required_asset_type": "Water",
        "status": "Active"
    }, headers=headers)
    assert res.status_code == 201, f"Failed to create location: {res.text}"
    
    # 2. Create Asset
    ast_id = f"UAT-AST-{int(time.time())}"
    res = client.post("/api/assets", json={
        "asset_id": ast_id,
        "serial_number": f"SN-{ast_id}",
        "asset_type": "Water",
        "capacity": "9L",
        "status": "Active"
    }, headers=headers)
    assert res.status_code == 201, f"Failed to create asset: {res.text}"
    
    # 3. Assign Asset
    res = client.post(f"/api/assets/{ast_id}/link/{loc_id}", json={
        "movement_reason": "UAT Scenario 1"
    }, headers=headers)
    assert res.status_code == 200, f"Failed to assign asset: {res.text}"
    
    # 4. Inspection Pass
    res = client.post("/api/inspections", json={
        "asset_id": ast_id,
        "location_id": loc_id,
        "inspector": "UAT Tester",
        "pressure": "Pass",
        "seal": "Pass",
        "pin": "Pass",
        "gauge": "Pass",
        "hose": "Pass",
        "nozzle": "Pass",
        "visibility": "Pass",
        "accessibility": "Pass",
        "mounting": "Pass",
        "safety_tag": "Pass",
        "cylinder_damage": "Pass",
        "overall_status": "Pass",
        "remarks": "Looks good"
    }, headers=headers)
    assert res.status_code == 201, f"Failed to pass inspection: {res.text}"
    print("Scenario 1 Passed")

def test_scenario_2_defect_workflow():
    print("--- Running Scenario 2: Defect Workflow ---")
    admin_token = login_as("admin@fireext.com")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Pre-req: Location and Asset
    loc_id = f"UAT-LOC-{int(time.time())+1}"
    client.post("/api/locations", json={
        "location_id": loc_id,
        "location_name": f"UAT Defect Room {loc_id}",
        "plant": "Head Office",
        "department": "Safety",
        "required_asset_type": "CO2",
        "status": "Active"
    }, headers=headers)
    
    ast_id = f"UAT-AST-{int(time.time())+1}"
    client.post("/api/assets", json={
        "asset_id": ast_id,
        "serial_number": f"SN-{ast_id}",
        "asset_type": "CO2",
        "capacity": "4.5kg",
        "status": "Active"
    }, headers=headers)
    
    client.post(f"/api/assets/{ast_id}/link/{loc_id}", json={"movement_reason": "UAT Scenario 2"}, headers=headers)
    
    # 1. Inspection Fail
    res = client.post("/api/inspections", json={
        "asset_id": ast_id,
        "location_id": loc_id,
        "inspector": "UAT Tester",
        "pressure": "Pass",
        "seal": "Fail",
        "pin": "Pass",
        "gauge": "Pass",
        "hose": "Pass",
        "nozzle": "Pass",
        "overall_status": "Fail",
        "remarks": "Broken seal"
    }, headers=headers)
    assert res.status_code == 201, "Failed inspection"
    
    # 2. Check Maintenance Auto-creation
    res = client.get(f"/api/maintenance?asset_id={ast_id}", headers=headers)
    tickets = res.json()["data"]
    assert len(tickets) > 0, "Maintenance ticket not auto-created"
    ticket_id = tickets[0]["maintenance_id"]
    
    # 3. Close Maintenance
    res = client.put(f"/api/maintenance/{ticket_id}/close", json={
        "verified_by": "UAT Admin",
        "remarks": "Seal replaced"
    }, headers=headers)
    assert res.status_code == 200, "Failed to close maintenance"
    
    print("Scenario 2 Passed")

def test_scenario_3_negative():
    print("--- Running Scenario 3: Negative/RBAC Testing ---")
    admin_token = login_as("admin@fireext.com")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Duplicate asset
    res = client.post("/api/assets", json={
        "asset_id": "UAT-DUP",
        "serial_number": "SN-DUP",
        "asset_type": "CO2",
    }, headers=headers)
    
    res2 = client.post("/api/assets", json={
        "asset_id": "UAT-DUP",
        "serial_number": "SN-DUP2",
        "asset_type": "CO2",
    }, headers=headers)
    assert res2.status_code == 400, "Failed to block duplicate asset creation"
    
    # Unauthorized access (No token)
    res3 = client.get("/api/dashboard/stats")
    assert res3.status_code == 401, "Failed to block unauthorized dashboard access"
    
    print("Scenario 3 Passed")

if __name__ == "__main__":
    try:
        test_scenario_1_asset_lifecycle()
        test_scenario_2_defect_workflow()
        test_scenario_3_negative()
        print("ALL UAT SCENARIOS PASSED SUCCESSFULLY")
    except AssertionError as e:
        print(f"UAT SCENARIO FAILED: {e}")
        sys.exit(1)
