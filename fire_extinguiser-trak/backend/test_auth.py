from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_auth_flow():
    print("1. Testing /api/auth/login")
    response = client.post(
        "/api/auth/login",
        data={"username": "admin@fireext.com", "password": "admin123"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"

    data = response.json()
    assert data["success"] is True

    token_data = data["data"]
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]

    print("Login successful")
    print(f"JWT Access Token created: {access_token[:20]}...")
    print(f"Refresh Token created: {refresh_token[:20]}...")

    headers = {"Authorization": f"Bearer {access_token}"}

    print("2. Testing /api/auth/me")
    me_response = client.get("/api/auth/me", headers=headers)
    assert me_response.status_code == 200, f"/me failed: {me_response.text}"
    print("/me endpoint returned user data successfully")

    print("3. Testing /api/auth/sessions")
    sessions_response = client.get("/api/auth/sessions", headers=headers)
    assert (
        sessions_response.status_code == 200
    ), f"/sessions failed: {sessions_response.text}"
    sessions_data = sessions_response.json()["data"]
    assert len(sessions_data) > 0, "No active sessions found"
    print(f"Session creation verified ({len(sessions_data)} active sessions)")


if __name__ == "__main__":
    try:
        test_auth_flow()
        print("\nAll authentication tests passed successfully!")
    except Exception as e:
        print(f"\nTest failed: {e}")
