from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def test_maintenance_submission():
    print("1. Logging in...")
    response = client.post(
        "/api/auth/login",
        data={"username": "admin@fireext.com", "password": "admin123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token_data = response.json()["data"]
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("2. Submitting maintenance ticket...")
    maint_resp = client.post(
        "/api/maintenance",
        headers=headers,
        json={
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
