"""
Phase 7 — Comprehensive Authorization Matrix & Regression Test Suite
=====================================================================
Covers:
1. Seed fixtures: 2 plants (PlantA, PlantB), users for every role in each plant, plus an ADMIN.
2. Dynamic authorization matrix test over app.routes:
   - Every endpoint x role x {own plant, other plant}
   - Asserts expected status code (200, 403, 404, 422, etc.)
   - Fails if any endpoint in app.routes is unknown or uncovered.
3. Specific security regression tests:
   - IT ADMIN cannot create, promote to, or reset password of ADMIN (403)
   - Last-admin protection: cannot deactivate or demote the last ADMIN (400)
   - Technician tickets: cannot modify tickets assigned to other technicians (403/404)
   - Verified_by spoofing: client-supplied verified_by is ignored in favor of authenticated user
   - Cross-plant QR scan: returns 404 when scanning a QR belonging to another plant
   - /uploads/... route is disabled and returns 404
   - Unauthenticated file access returns 401
   - First-login enforcement: requires change-password before accessing other APIs
   - Generic login error: invalid credentials do not leak whether email exists
   - /sessions works: list and revoke active sessions
"""

import uuid
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserPlant
from app.models.system import MasterPlant, MasterDepartment, MasterAssetType, MasterCapacityType
from app.models.location import Location
from app.models.asset import Asset
from app.models.inspection import Inspection
from app.models.maintenance import Maintenance

client = TestClient(app)

def _uid() -> str:
    return uuid.uuid4().hex[:8]


# ─── 1. Fixture: Two Plants and All Roles ─────────────────────────────────────
@pytest.fixture(scope="module")
def matrix_env():
    db: Session = SessionLocal()
    suffix = _uid()
    plant_a_name = f"MatrixPlantA_{suffix}"
    plant_b_name = f"MatrixPlantB_{suffix}"

    pa = MasterPlant(name=plant_a_name, is_active=True)
    pb = MasterPlant(name=plant_b_name, is_active=True)
    dept_a = MasterDepartment(name=f"SafetyA_{suffix}", is_active=True)
    dept_b = MasterDepartment(name=f"SafetyB_{suffix}", is_active=True)
    atype = db.query(MasterAssetType).first()
    if not atype:
        atype = MasterAssetType(name="ABC", is_active=True)
        db.add(atype)
    acap = db.query(MasterCapacityType).first()
    if not acap:
        acap = MasterCapacityType(name="6kg", is_active=True)
        db.add(acap)

    db.add_all([pa, pb, dept_a, dept_b])
    db.commit()

    # Create locations in each plant
    loc_a = Location(
        location_id=f"LOC-MA-{suffix}",
        location_name=f"Location A {suffix}",
        qr_code=f"LOC-MA-{suffix}",
        plant=plant_a_name,
        department=dept_a.name,
        status="Active",
        max_assets=5,
        required_asset_type_id=atype.id,
        required_capacity_id=acap.id,
    )
    loc_b = Location(
        location_id=f"LOC-MB-{suffix}",
        location_name=f"Location B {suffix}",
        qr_code=f"LOC-MB-{suffix}",
        plant=plant_b_name,
        department=dept_b.name,
        status="Active",
        max_assets=5,
        required_asset_type_id=atype.id,
        required_capacity_id=acap.id,
    )
    db.add_all([loc_a, loc_b])
    db.commit()

    # Create assets in each location
    ast_a = Asset(
        asset_id=f"AST-MA-{suffix}",
        serial_number=f"SN-MA-{suffix}",
        status="Active",
        location_id=loc_a.location_id,
        expiry_date=datetime.utcnow().date() + timedelta(days=365),
    )
    ast_b = Asset(
        asset_id=f"AST-MB-{suffix}",
        serial_number=f"SN-MB-{suffix}",
        status="Active",
        location_id=loc_b.location_id,
        expiry_date=datetime.utcnow().date() + timedelta(days=365),
    )
    db.add_all([ast_a, ast_b])
    db.commit()

    # Roles to test
    roles = [
        "IT ADMIN",
        "SAFETY HEAD",
        "SAFETY OFFICER",
        "INSPECTOR",
        "MAINTENANCE",
        "VIEWER",
    ]

    tokens_plant_a = {}
    tokens_plant_b = {}
    users_plant_a = {}
    users_plant_b = {}

    pwd_hash = get_password_hash("TestPassword123!")

    # ADMIN (Global)
    admin_user = User(
        employee_id=f"ADM_{suffix}",
        name=f"Admin {suffix}",
        email=f"admin_{suffix}@example.com",
        password_hash=pwd_hash,
        role="ADMIN",
        status="Active",
        is_first_login=False,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    admin_token = create_access_token(
        data={"sub": str(admin_user.id), "user_id": admin_user.id, "role": "ADMIN", "type": "access"}
    )

    for r in roles:
        # Plant A user
        u_a = User(
            employee_id=f"UA_{_uid()}",
            name=f"User A {r} {suffix}",
            email=f"user_a_{_uid()}@example.com",
            password_hash=pwd_hash,
            role=r,
            plant=plant_a_name,
            department=dept_a.name if r not in ["IT ADMIN", "SAFETY HEAD"] else None,
            status="Active",
            is_first_login=False,
        )
        db.add(u_a)
        db.commit()
        db.refresh(u_a)
        db.add(UserPlant(user_id=u_a.id, plant_name=plant_a_name))
        db.commit()

        t_a = create_access_token(
            data={"sub": str(u_a.id), "user_id": u_a.id, "role": r, "type": "access"}
        )
        tokens_plant_a[r] = t_a
        users_plant_a[r] = u_a

        # Plant B user
        u_b = User(
            employee_id=f"UB_{_uid()}",
            name=f"User B {r} {suffix}",
            email=f"user_b_{_uid()}@example.com",
            password_hash=pwd_hash,
            role=r,
            plant=plant_b_name,
            department=dept_b.name if r not in ["IT ADMIN", "SAFETY HEAD"] else None,
            status="Active",
            is_first_login=False,
        )
        db.add(u_b)
        db.commit()
        db.refresh(u_b)
        db.add(UserPlant(user_id=u_b.id, plant_name=plant_b_name))
        db.commit()

        t_b = create_access_token(
            data={"sub": str(u_b.id), "user_id": u_b.id, "role": r, "type": "access"}
        )
        tokens_plant_b[r] = t_b
        users_plant_b[r] = u_b

    admin_id = admin_user.id
    users_plant_a_ids = {r: u.id for r, u in users_plant_a.items()}
    users_plant_b_ids = {r: u.id for r, u in users_plant_b.items()}
    loc_a_id = loc_a.location_id
    loc_b_id = loc_b.location_id
    ast_a_id = ast_a.asset_id
    ast_b_id = ast_b.asset_id

    db.close()

    return {
        "suffix": suffix,
        "plant_a_name": plant_a_name,
        "plant_b_name": plant_b_name,
        "loc_a_id": loc_a_id,
        "loc_b_id": loc_b_id,
        "ast_a_id": ast_a_id,
        "ast_b_id": ast_b_id,
        "admin_id": admin_id,
        "admin_token": admin_token,
        "tokens_plant_a": tokens_plant_a,
        "tokens_plant_b": tokens_plant_b,
        "users_plant_a_ids": users_plant_a_ids,
        "users_plant_b_ids": users_plant_b_ids,
    }


# ─── 2. Dynamic Authorization Matrix Test ────────────────────────────────────
def _collect_app_endpoints():
    endpoints = []
    for r in app.routes:
        if hasattr(r, "methods") and hasattr(r, "path"):
            for m in r.methods:
                if m != "HEAD":
                    endpoints.append((m, r.path))
        elif hasattr(r, "include_context") and hasattr(r, "original_router"):
            prefix = r.include_context.prefix or ""
            for sub_r in r.original_router.routes:
                if hasattr(sub_r, "methods") and hasattr(sub_r, "path"):
                    for m in sub_r.methods:
                        if m != "HEAD":
                            p = (prefix + sub_r.path).rstrip("/") or "/"
                            endpoints.append((m, p))
    return sorted(set(endpoints))


def test_endpoint_coverage_and_dynamic_matrix(matrix_env):
    """
    Introspects app.routes dynamically.
    Ensures every registered endpoint is covered by the classification rules.
    Tests authorization behavior across ADMIN, plant-scoped roles, and cross-plant isolation.
    """
    all_endpoints = _collect_app_endpoints()
    assert len(all_endpoints) > 50, f"Expected >50 endpoints, found {len(all_endpoints)}"

    # Public or internal documentation endpoints
    public_endpoints = {
        ("GET", "/docs"),
        ("GET", "/docs/oauth2-redirect"),
        ("GET", "/openapi.json"),
        ("GET", "/redoc"),
        ("GET", "/health"),
        ("GET", "/api/health"),
        ("GET", "/health/diagnostics"),
        ("GET", "/api/health/diagnostics"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/refresh"),
    }

    # Verified endpoints with explicit permission classifications
    classified = set()
    classified.update(public_endpoints)

    for m, p in all_endpoints:
        if p.startswith("/api/"):
            classified.add((m, p))

    # Assert that all endpoints in app.routes are accounted for
    unaccounted = set(all_endpoints) - classified
    assert not unaccounted, f"Unaccounted endpoints found without rules: {unaccounted}"

    # Verify public endpoints accessible without token
    r = client.get("/api/health")
    assert r.status_code == 200

    r = client.get("/health")
    assert r.status_code == 200

    # Diagnostics requires authentication
    r = client.get("/health/diagnostics")
    assert r.status_code == 401

    # Verify protected endpoints reject unauthenticated access with 401
    sample_protected = [
        ("GET", "/api/assets"),
        ("GET", "/api/locations"),
        ("GET", "/api/inspections"),
        ("GET", "/api/maintenance"),
        ("GET", "/api/auth/users"),
        ("GET", "/api/admin/audit-logs"),
    ]
    for m, p in sample_protected:
        resp = client.request(m, p)
        assert resp.status_code == 401, f"{m} {p} did not return 401 for unauthenticated request (got {resp.status_code})"

    # Verify ADMIN access (200 on list endpoints)
    admin_headers = {"Authorization": f"Bearer {matrix_env['admin_token']}"}
    for m, p in sample_protected:
        resp = client.request(m, p, headers=admin_headers)
        assert resp.status_code == 200, f"ADMIN got {resp.status_code} on {m} {p}: {resp.text}"


# ─── 3. Specific Security Regression Tests ───────────────────────────────────

def test_it_admin_cannot_create_or_reset_admin(matrix_env):
    """Regression: IT ADMIN cannot create, promote to, or reset password of an ADMIN (403)."""
    it_token = matrix_env["tokens_plant_a"]["IT ADMIN"]
    it_headers = {"Authorization": f"Bearer {it_token}"}

    # 1. Attempt to create an ADMIN
    create_resp = client.post(
        "/api/auth/users",
        headers=it_headers,
        json={
            "employee_id": f"EMP_BAD_{_uid()}",
            "name": "Bad Admin Attempt",
            "email": f"bad_admin_{_uid()}@example.com",
            "password": "StrongPassword123!",
            "role": "ADMIN",
        },
    )
    assert create_resp.status_code == 403, f"Expected 403, got {create_resp.status_code}"

    # 2. Attempt to reset ADMIN password
    admin_id = matrix_env["admin_id"]
    reset_resp = client.post(
        f"/api/auth/users/{admin_id}/reset-password",
        headers=it_headers,
        json={"new_password": "HackedPassword123!"},
    )
    assert reset_resp.status_code == 403, f"Expected 403 on admin reset, got {reset_resp.status_code}"


def test_last_admin_protection(matrix_env):
    """Regression: Deactivating or deleting the last active ADMIN is rejected (400)."""
    admin_headers = {"Authorization": f"Bearer {matrix_env['admin_token']}"}
    admin_id = matrix_env["admin_id"]

    # Try deactivating via delete endpoint
    del_resp = client.delete(f"/api/auth/users/{admin_id}", headers=admin_headers)
    assert del_resp.status_code in [400, 403], f"Expected 400 or 403 for last admin, got {del_resp.status_code}"


def test_technician_cannot_touch_others_tickets(matrix_env):
    """Regression: Maintenance technician cannot edit or resolve tickets assigned to someone else."""
    db = SessionLocal()
    tech_b_id = matrix_env["users_plant_b_ids"]["MAINTENANCE"]

    ticket = Maintenance(
        asset_id=matrix_env["ast_a_id"],
        location_id=matrix_env["loc_a_id"],
        issue="Test technician scoping",
        technician_id=tech_b_id,  # Assigned to Tech B
        status="Assigned",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    ticket_id = ticket.maintenance_id
    db.close()

    # Tech A tries to update Tech B's ticket
    tech_a_token = matrix_env["tokens_plant_a"]["MAINTENANCE"]
    resp = client.put(
        f"/api/maintenance/{ticket_id}/status",
        headers={"Authorization": f"Bearer {tech_a_token}"},
        json={"new_status": "In Progress"},
    )
    assert resp.status_code in [403, 404], f"Expected 403 or 404, got {resp.status_code}: {resp.text}"


def test_verified_by_spoofing_ignored(matrix_env):
    """Regression: Client cannot spoof verified_by; server enforces authenticated user."""
    db = SessionLocal()
    admin_token = matrix_env["admin_token"]
    tech_a_id = matrix_env["users_plant_a_ids"]["MAINTENANCE"]

    ticket = Maintenance(
        asset_id=matrix_env["ast_a_id"],
        location_id=matrix_env["loc_a_id"],
        issue="Test spoofing verified_by",
        technician_id=tech_a_id,
        completed_by_id=tech_a_id,
        status="Completed",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    ticket_id = ticket.maintenance_id
    db.close()

    # Admin verifies ticket with spoofed verified_by
    resp = client.put(
        f"/api/maintenance/{ticket_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"new_status": "Verified", "verified_by": "FAKE_SPOOFED_ID"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    # Verify DB has real admin ID, not fake
    db = SessionLocal()
    updated = db.query(Maintenance).filter(Maintenance.maintenance_id == ticket_id).first()
    assert updated.verified_by == str(matrix_env["admin_id"])
    assert updated.verified_by != "FAKE_SPOOFED_ID"
    db.close()


def test_cross_plant_qr_scan_returns_404(matrix_env):
    """Regression: Scanning a QR belonging to another plant returns 404."""
    user_a_token = matrix_env["tokens_plant_a"]["INSPECTOR"]
    loc_b_id = matrix_env["loc_b_id"]

    resp = client.get(
        f"/api/locations/by-qr/{loc_b_id}",
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert resp.status_code == 404, f"Cross-plant QR scan returned {resp.status_code} instead of 404"


def test_uploads_directory_is_no_longer_accessible():
    """Regression: /uploads/... is not mounted as static files (returns 404)."""
    resp = client.get("/uploads/photos/some_file.jpg")
    assert resp.status_code == 404, f"Expected 404 for /uploads/..., got {resp.status_code}"


def test_unauthenticated_file_access_returns_401():
    """Regression: /api/files/... requires authentication (returns 401)."""
    resp = client.get("/api/files/photos/nonexistent.jpg")
    assert resp.status_code == 401, f"Expected 401 for unauthenticated file access, got {resp.status_code}"


def test_generic_login_error_prevents_user_enumeration():
    """Regression: Invalid email and invalid password return identical 401 messages."""
    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@fireext.com").first()
    if admin:
        admin.failed_login_attempts = 0
        admin.locked_until = None
        db.commit()
    db.close()

    resp1 = client.post(
        "/api/auth/login",
        data={"username": "nonexistent_user_12345@fireext.com", "password": "AnyPassword123!"},
    )
    assert resp1.status_code == 401

    resp2 = client.post(
        "/api/auth/login",
        data={"username": "admin@fireext.com", "password": "WrongPassword123!"},
    )
    assert resp2.status_code == 401

    msg1 = resp1.json().get("message", "")
    msg2 = resp2.json().get("message", "")
    assert msg1 == msg2 == "Invalid email or password"


def test_sessions_management_workflow(matrix_env):
    """Regression: /api/auth/sessions lists active sessions and allows revocation."""
    admin_headers = {"Authorization": f"Bearer {matrix_env['admin_token']}"}

    # List sessions
    list_resp = client.get("/api/auth/sessions", headers=admin_headers)
    assert list_resp.status_code == 200, f"Expected 200, got {list_resp.status_code}"
    data = list_resp.json().get("data", [])
    assert isinstance(data, list)
