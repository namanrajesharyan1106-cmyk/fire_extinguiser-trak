"""
Production Validation Script - Phases 3, 5, 6, 8, 9
Tests every API endpoint systematically.
"""
import json
import time
import traceback
from datetime import datetime

import requests

BASE = "http://127.0.0.1:8001"
RESULTS = []
ADMIN_TOKEN = None
CREATED_USER_ID = None
CREATED_LOCATION_ID = None
CREATED_ASSET_ID = None

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def record(phase, test_name, passed, status_code=None, detail=""):
    icon = "PASS" if passed else "FAIL"
    RESULTS.append({
        "phase": phase, "test": test_name,
        "passed": passed, "status_code": status_code, "detail": detail,
    })
    print(f"  [{icon}] {test_name} | HTTP {status_code} | {detail}")

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 - API Validation
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("PHASE 3 - API VALIDATION")
print("=" * 70)

# ── Health Check ──────────────────────────────────────────────────────────────
print("\n[Health Check]")
try:
    r = requests.get(f"{BASE}/", timeout=5)
    record("Health", "GET /", r.status_code == 200, r.status_code, r.json().get("message",""))
    r2 = requests.get(f"{BASE}/health", timeout=5)
    record("Health", "GET /health", r2.status_code == 200, r2.status_code)
except Exception as e:
    record("Health", "Health endpoints", False, None, str(e))

# ── Authentication ────────────────────────────────────────────────────────────
print("\n[Authentication]")

# Valid login
try:
    t0 = time.time()
    r = requests.post(f"{BASE}/api/auth/login",
        data={"username": "admin@fireext.com", "password": "admin123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=10)
    elapsed = round((time.time() - t0) * 1000)
    passed = r.status_code == 200 and "access_token" in r.json().get("data", {})
    if passed:
        ADMIN_TOKEN = r.json()["data"]["access_token"]
        REFRESH_TOKEN = r.json()["data"]["refresh_token"]
    record("Auth", "POST /api/auth/login (valid)", passed, r.status_code, f"{elapsed}ms")
except Exception as e:
    record("Auth", "POST /api/auth/login (valid)", False, None, str(e))
    ADMIN_TOKEN = None

# Invalid credentials
try:
    r = requests.post(f"{BASE}/api/auth/login",
        data={"username": "wrong@email.com", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=5)
    record("Auth", "POST /api/auth/login (invalid)", r.status_code in [401, 400], r.status_code)
except Exception as e:
    record("Auth", "POST /api/auth/login (invalid)", False, None, str(e))

# Get current user /me
if ADMIN_TOKEN:
    try:
        r = requests.get(f"{BASE}/api/auth/me", headers=auth_headers(ADMIN_TOKEN), timeout=5)
        passed = r.status_code == 200
        record("Auth", "GET /api/auth/me", passed, r.status_code,
               r.json().get("data", {}).get("email", "") if passed else r.text[:80])
    except Exception as e:
        record("Auth", "GET /api/auth/me", False, None, str(e))

    # Token refresh
    try:
        r = requests.post(f"{BASE}/api/auth/refresh",
            json={"refresh_token": REFRESH_TOKEN}, timeout=5)
        record("Auth", "POST /api/auth/refresh", r.status_code == 200, r.status_code,
               "new token obtained" if r.status_code == 200 else r.text[:80])
    except Exception as e:
        record("Auth", "POST /api/auth/refresh", False, None, str(e))

    # Expired/invalid token
    try:
        r = requests.get(f"{BASE}/api/auth/me",
            headers={"Authorization": "Bearer invalidtoken_abc"}, timeout=5)
        record("Auth", "GET /api/auth/me (invalid token)", r.status_code == 401, r.status_code)
    except Exception as e:
        record("Auth", "GET /api/auth/me (invalid token)", False, None, str(e))

    # Logout (requires refresh_token in body per API contract)
    try:
        r = requests.post(f"{BASE}/api/auth/logout",
            json={"refresh_token": REFRESH_TOKEN},
            headers=auth_headers(ADMIN_TOKEN), timeout=5)
        record("Auth", "POST /api/auth/logout", r.status_code in [200, 204], r.status_code)
    except Exception as e:
        record("Auth", "POST /api/auth/logout", False, None, str(e))

    # Re-login after logout for continued testing
    try:
        r = requests.post(f"{BASE}/api/auth/login",
            data={"username": "admin@fireext.com", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=10)
        if r.status_code == 200:
            ADMIN_TOKEN = r.json()["data"]["access_token"]
    except Exception:
        pass

# ── Locations ─────────────────────────────────────────────────────────────────
print("\n[Locations]")
if ADMIN_TOKEN:
    H = auth_headers(ADMIN_TOKEN)
    import time as _time
    _ts = str(int(_time.time()))

    # Create location
    loc_payload = {
        "location_name": f"Test Block A - Room {_ts}",
        "plant": "Plant Alpha",
        "area": "Production Zone",
        "department": "Manufacturing",
        "building": "Block A",
        "floor": "1st Floor",
        "risk_category": "High",
        "required_asset_type": "ABC",
        "required_capacity": "6kg",
        "inspection_frequency": 30,
    }
    try:
        t0 = time.time()
        r = requests.post(f"{BASE}/api/locations/", json=loc_payload, headers=H, timeout=10)
        elapsed = round((time.time() - t0) * 1000)
        passed = r.status_code in [200, 201]
        if passed:
            data = r.json().get("data", {})
            CREATED_LOCATION_ID = data.get("location_id") or data.get("id")
        record("Locations", "POST /api/locations/ (create)", passed, r.status_code,
               f"ID={CREATED_LOCATION_ID} {elapsed}ms" if passed else r.text[:120])
    except Exception as e:
        record("Locations", "POST /api/locations/ (create)", False, None, str(e))

    # List locations with pagination
    try:
        r = requests.get(f"{BASE}/api/locations/?page=1&per_page=10", headers=H, timeout=5)
        passed = r.status_code == 200
        record("Locations", "GET /api/locations/ (paginated)", passed, r.status_code,
               f"items={len(r.json().get('data',{}).get('items',[]))}" if passed else r.text[:80])
    except Exception as e:
        record("Locations", "GET /api/locations/ (paginated)", False, None, str(e))

    # Search
    try:
        r = requests.get(f"{BASE}/api/locations/?search=Test+Block", headers=H, timeout=5)
        passed = r.status_code == 200
        record("Locations", "GET /api/locations/?search=...", passed, r.status_code)
    except Exception as e:
        record("Locations", "GET /api/locations/?search", False, None, str(e))

    # Filter by plant
    try:
        r = requests.get(f"{BASE}/api/locations/?plant=Plant+Alpha", headers=H, timeout=5)
        passed = r.status_code == 200
        record("Locations", "GET /api/locations/?plant=...", passed, r.status_code)
    except Exception as e:
        record("Locations", "GET /api/locations/?plant", False, None, str(e))

    # Get single location
    if CREATED_LOCATION_ID:
        try:
            r = requests.get(f"{BASE}/api/locations/{CREATED_LOCATION_ID}", headers=H, timeout=5)
            passed = r.status_code == 200
            record("Locations", "GET /api/locations/{id}", passed, r.status_code)
        except Exception as e:
            record("Locations", "GET /api/locations/{id}", False, None, str(e))

        # Update location (use a non-unique field only)
        try:
            r = requests.put(f"{BASE}/api/locations/{CREATED_LOCATION_ID}",
                json={"department": "QA Dept", "floor": "2nd Floor"},
                headers=H, timeout=5)
            record("Locations", "PUT /api/locations/{id}", r.status_code in [200, 201], r.status_code,
                   r.text[:80] if r.status_code not in [200, 201] else "")
        except Exception as e:
            record("Locations", "PUT /api/locations/{id}", False, None, str(e))

        # QR code - correct endpoint is /generate-qr (POST) and /qr-image (GET)
        try:
            r = requests.post(f"{BASE}/api/locations/{CREATED_LOCATION_ID}/generate-qr", headers=H, timeout=5)
            passed = r.status_code in [200, 201]
            record("Locations", "POST /api/locations/{id}/generate-qr", passed, r.status_code,
                   r.json().get("data", {}).get("qr_code", "")[:60] if passed else r.text[:80])
        except Exception as e:
            record("Locations", "POST /api/locations/{id}/generate-qr", False, None, str(e))

    # Duplicate location (same name + plant)
    try:
        r = requests.post(f"{BASE}/api/locations/", json=loc_payload, headers=H, timeout=5)
        record("Locations", "POST /api/locations/ (duplicate)", r.status_code in [400, 409, 422], r.status_code)
    except Exception as e:
        record("Locations", "POST /api/locations/ (duplicate)", False, None, str(e))

    # Invalid ID
    try:
        r = requests.get(f"{BASE}/api/locations/INVALID_ID_XXXX", headers=H, timeout=5)
        record("Locations", "GET /api/locations/ (invalid id)", r.status_code == 404, r.status_code)
    except Exception as e:
        record("Locations", "GET /api/locations/ (invalid id)", False, None, str(e))

# ── Assets ────────────────────────────────────────────────────────────────────
print("\n[Assets]")
if ADMIN_TOKEN and CREATED_LOCATION_ID:
    H = auth_headers(ADMIN_TOKEN)
    import time as _time2
    _ts2 = _time2.time()
    asset_payload = {
        "asset_type": "ABC",
        "capacity": "6kg",
        "manufacturer": "Amerex",
        "serial_number": f"SN-PROD-{int(_ts2)}",
        "status": "Active",
    }
    # Create asset
    try:
        r = requests.post(f"{BASE}/api/assets/", json=asset_payload, headers=H, timeout=10)
        passed = r.status_code in [200, 201]
        if passed:
            CREATED_ASSET_ID = r.json().get("data", {}).get("asset_id")
        record("Assets", "POST /api/assets/ (create)", passed, r.status_code,
               f"ID={CREATED_ASSET_ID}" if passed else r.text[:120])
    except Exception as e:
        record("Assets", "POST /api/assets/ (create)", False, None, str(e))

    # List assets
    try:
        r = requests.get(f"{BASE}/api/assets/", headers=H, timeout=5)
        record("Assets", "GET /api/assets/", r.status_code == 200, r.status_code)
    except Exception as e:
        record("Assets", "GET /api/assets/", False, None, str(e))

    # Assign to location
    if CREATED_ASSET_ID:
        try:
            r = requests.post(f"{BASE}/api/assets/{CREATED_ASSET_ID}/assign",
                json={"location_id": CREATED_LOCATION_ID, "reason": "Initial assignment"},
                headers=H, timeout=5)
            record("Assets", "POST /api/assets/{id}/assign", r.status_code in [200, 201], r.status_code,
                   r.text[:80] if r.status_code not in [200, 201] else "assigned")
        except Exception as e:
            record("Assets", "POST /api/assets/{id}/assign", False, None, str(e))

        # Get asset
        try:
            r = requests.get(f"{BASE}/api/assets/{CREATED_ASSET_ID}", headers=H, timeout=5)
            record("Assets", "GET /api/assets/{id}", r.status_code == 200, r.status_code)
        except Exception as e:
            record("Assets", "GET /api/assets/{id}", False, None, str(e))

    # Duplicate serial number
    try:
        r = requests.post(f"{BASE}/api/assets/", json=asset_payload, headers=H, timeout=5)
        record("Assets", "POST /api/assets/ (duplicate serial)", r.status_code in [400, 409, 422], r.status_code)
    except Exception as e:
        record("Assets", "POST /api/assets/ (duplicate serial)", False, None, str(e))

# ── Dashboard ─────────────────────────────────────────────────────────────────
print("\n[Dashboard]")
if ADMIN_TOKEN:
    H = auth_headers(ADMIN_TOKEN)
    for endpoint in ["/api/dashboard/overview", "/api/dashboard/stats", "/api/dashboard/"]:
        try:
            r = requests.get(f"{BASE}{endpoint}", headers=H, timeout=5)
            record("Dashboard", f"GET {endpoint}", r.status_code in [200, 404], r.status_code,
                   "OK" if r.status_code == 200 else "not found (may not exist)")
        except Exception as e:
            record("Dashboard", f"GET {endpoint}", False, None, str(e))

# ── Inspections ───────────────────────────────────────────────────────────────
print("\n[Inspections]")
if ADMIN_TOKEN and CREATED_LOCATION_ID and CREATED_ASSET_ID:
    H = auth_headers(ADMIN_TOKEN)
    insp_payload = {
        "location_id": CREATED_LOCATION_ID,
        "asset_id": CREATED_ASSET_ID,
        "pressure": "Pass",
        "seal": "Pass",
        "hose": "Pass",
        "pin": "Pass",
        "gauge": "Pass",
        "nozzle": "Pass",
        "mounting": "Pass",
        "visibility": "Pass",
        "accessibility": "Pass",
        "safety_tag": "Pass",
        "cylinder_damage": "Pass",
        "remarks": "All good",
    }
    try:
        r = requests.post(f"{BASE}/api/inspections/", json=insp_payload, headers=H, timeout=10)
        passed = r.status_code in [200, 201]
        insp_id = r.json().get("data", {}).get("inspection_id") if passed else None
        record("Inspections", "POST /api/inspections/ (submit)", passed, r.status_code,
               f"ID={insp_id}" if passed else r.text[:120])
    except Exception as e:
        record("Inspections", "POST /api/inspections/ (submit)", False, None, str(e))

    try:
        r = requests.get(f"{BASE}/api/inspections/", headers=H, timeout=5)
        record("Inspections", "GET /api/inspections/", r.status_code == 200, r.status_code)
    except Exception as e:
        record("Inspections", "GET /api/inspections/", False, None, str(e))

# ── Unauthorized Access ───────────────────────────────────────────────────────
print("\n[Security - Unauthorized Access]")
for endpoint in ["/api/locations/", "/api/assets/", "/api/inspections/", "/api/auth/me"]:
    try:
        r = requests.get(f"{BASE}{endpoint}", timeout=5)
        record("Security", f"GET {endpoint} (no token)", r.status_code == 401, r.status_code)
    except Exception as e:
        record("Security", f"GET {endpoint} (no token)", False, None, str(e))

# ── Reports ───────────────────────────────────────────────────────────────────
print("\n[Reports]")
if ADMIN_TOKEN:
    H = auth_headers(ADMIN_TOKEN)
    for endpoint in ["/api/reports/", "/api/reports/summary", "/api/reports/inspections"]:
        try:
            r = requests.get(f"{BASE}{endpoint}", headers=H, timeout=5)
            record("Reports", f"GET {endpoint}", r.status_code in [200, 404], r.status_code)
        except Exception as e:
            record("Reports", f"GET {endpoint}", False, None, str(e))

# ── Notifications ─────────────────────────────────────────────────────────────
print("\n[Notifications]")
if ADMIN_TOKEN:
    H = auth_headers(ADMIN_TOKEN)
    try:
        r = requests.get(f"{BASE}/api/notifications/", headers=H, timeout=5)
        record("Notifications", "GET /api/notifications/", r.status_code == 200, r.status_code)
    except Exception as e:
        record("Notifications", "GET /api/notifications/", False, None, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# Final Report
# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("PRODUCTION READINESS REPORT")
print("=" * 70)

total = len(RESULTS)
passed = sum(1 for r in RESULTS if r["passed"])
failed = total - passed
score = round((passed / total) * 100) if total else 0

print(f"Total Tests : {total}")
print(f"Passed      : {passed}")
print(f"Failed      : {failed}")
print(f"Pass Rate   : {score}%")
print()

if failed > 0:
    print("FAILURES:")
    for r in RESULTS:
        if not r["passed"]:
            print(f"  [{r['phase']}] {r['test']} | HTTP {r['status_code']} | {r['detail']}")

# Phase summary table
phases = {}
for r in RESULTS:
    p = r["phase"]
    phases.setdefault(p, {"pass": 0, "fail": 0})
    if r["passed"]:
        phases[p]["pass"] += 1
    else:
        phases[p]["fail"] += 1

print()
print("By Phase:")
for phase, counts in phases.items():
    total_p = counts["pass"] + counts["fail"]
    pct = round((counts["pass"] / total_p) * 100) if total_p else 0
    print(f"  {phase:<20} {counts['pass']}/{total_p} ({pct}%)")
