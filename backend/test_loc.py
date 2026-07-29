import requests

url = "http://127.0.0.1:8000/api/locations"
# You may need to obtain an auth token first. Let's assume we can login.
auth_url = "http://127.0.0.1:8000/api/auth/login"
token = None

res = requests.post(auth_url, data={"username": "admin", "password": "password"})
if res.status_code == 200:
    token = res.json()["access_token"]
    print("Got token")
else:
    print("Login failed:", res.text)
    
if token:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "location_name": "Test Location 123",
        "plant": "PP02",
        "area": "Assembly",
        "department": "Production",
        "building": "Main Building",
        "floor": "Ground",
        "required_asset_type_id": 1,
        "required_capacity_id": 1,
        "risk_category": "Medium",
        "status": "Active"
    }
    res = requests.post(url, json=payload, headers=headers)
    print("Response Code:", res.status_code)
    print("Response Body:", res.text)
