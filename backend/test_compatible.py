import requests

auth_url = "http://127.0.0.1:8000/api/auth/login"
res = requests.post(auth_url, data={"username": "admin", "password": "password"})
if res.status_code == 200:
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # First get an asset ID
    asset_res = requests.get("http://127.0.0.1:8000/api/assets", headers=headers)
    if asset_res.status_code == 200 and len(asset_res.json()["data"]["items"]) > 0:
        asset_id = asset_res.json()["data"]["items"][0]["asset_id"]
        print(f"Testing compatibility for Asset ID: {asset_id}")
        
        comp_res = requests.get(f"http://127.0.0.1:8000/api/assets/{asset_id}/compatible-locations", headers=headers)
        print("Status:", comp_res.status_code)
        
        if comp_res.status_code == 200:
            data = comp_res.json()["data"]
            print(f"Compatible Locations: {len(data['compatible'])}")
            print(f"Rejected Locations: {len(data['rejected'])}")
            if len(data['rejected']) > 0:
                print("Sample rejection:")
                print(data['rejected'][0]['location_id'], data['rejected'][0]['rejection_reasons'])
        else:
            print(comp_res.text)
else:
    print("Login failed")
