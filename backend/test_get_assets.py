import requests

auth_url = "http://127.0.0.1:8000/api/auth/login"
res = requests.post(auth_url, data={"username": "admin", "password": "password"})
if res.status_code == 200:
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get("http://127.0.0.1:8000/api/assets", headers=headers)
    print("Status:", res.status_code)
    print("Response:", res.text[:500])
else:
    print("Login failed")
