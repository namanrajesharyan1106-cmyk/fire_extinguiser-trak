from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_users_list():
    print("1. Logging in as Admin...")
    response = client.post(
        "/api/auth/login",
        data={"username": "admin@fireext.com", "password": "admin123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token_data = response.json()["data"]
    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("2. Fetching users list...")
    resp = client.get("/api/auth/users", headers=headers)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Error: {resp.text}")
    assert resp.status_code == 200, "Users list fetch failed"
    data = resp.json()
    print(f"Successfully retrieved {len(data['data'])} users")

if __name__ == "__main__":
    test_users_list()
    print("Test passed!")
