from fastapi.testclient import TestClient
import uuid
from app.main import app

client = TestClient(app)

def test_inspection_submission():
    print("1. Logging in to get access token...")
    response = client.post(
        "/api/auth/login",
        data={"username": "admin@fireext.com", "password": "admin123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token_data = response.json()["data"]
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("2. Creating a test location...")
    test_loc_id = f"TEST-LOC-{uuid.uuid4().hex[:6]}"
    loc_resp = client.post(
        "/api/locations",
        headers=headers,
        json={
            "location_id": test_loc_id,
            "location_name": "Test Location",
            "plant": "Test Plant"
        }
    )
    assert loc_resp.status_code == 201, f"Failed to create location: {loc_resp.text}"
    print(f"Location {test_loc_id} created successfully.")
    
    print("3. Submitting an inspection...")
    insp_resp = client.post(
        "/api/inspections",
        headers=headers,
        json={
            "location_id": test_loc_id,
            "pressure": "Pass",
            "seal": "Pass",
            "remarks": "Regression test for duplicate kwargs"
        }
    )
    assert insp_resp.status_code == 201, f"Inspection submission failed: {insp_resp.text}"
    insp_data = insp_resp.json()
    print(f"Inspection {insp_data.get('inspection_id')} created successfully!")
    
    print("4. Cleaning up (deleting test location)...")
    del_resp = client.delete(f"/api/locations/{test_loc_id}", headers=headers)
    assert del_resp.status_code == 200, f"Failed to delete location: {del_resp.text}"
    print("Cleanup successful.")

if __name__ == "__main__":
    try:
        test_inspection_submission()
        print("\nAll inspection regression tests passed successfully!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import sys
        sys.exit(1)
