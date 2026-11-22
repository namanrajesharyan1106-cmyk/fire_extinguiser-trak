from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def test_user_creation():
    print("1. Logging in as Admin...")
    response = client.post(
        "/api/auth/login",
        data={"username": "admin@fireext.com", "password": "admin123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token_data = response.json()["data"]
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("2. Creating new user...")
    emp_id = str(uuid.uuid4())[:8]
    email = f"test_{emp_id}@example.com"
    resp = client.post(
        "/api/auth/users",
        headers=headers,
        json={
            "employee_id": emp_id,
            "name": "Test User",
            "email": email,
            "password": "Password123!",
            "role": "SAFETY OFFICER",
            "department": "Safety",
            "plant": "HQ",
            "status": "Active"
        }
    )
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 201:
        print(f"Response: {resp.text}")
    assert resp.status_code == 201, f"User creation failed"

if __name__ == "__main__":
    test_user_creation()
    print("Test passed!")
