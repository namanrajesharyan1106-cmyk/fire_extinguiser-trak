"""
Phase 2 — Plant / Department Scoping Tests
===========================================
Verifies that each user sees ONLY data in their assigned plant(s), that cross-plant
accesses return 404 (not 403), that the ADMIN role sees everything, and that a user
with no plant assignment gets empty results (fail-closed).
"""

import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserPlant
from app.models.location import Location
from app.models.asset import Asset
from app.models.system import MasterAssetType, MasterCapacityType

client = TestClient(app)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _make_user(db: Session, plant: str, role: str = "SAFETY OFFICER") -> User:
    uid = _uid()
    user = User(
        employee_id=f"SC_{uid}",
        name=f"Scope User {uid}",
        email=f"scope_{uid}@test.com",
        password_hash=get_password_hash("ScopeTest123!"),
        role=role,
        department="Safety",
        plant=plant,
        status="Active",
        is_first_login=False,
    )
    db.add(user)
    db.flush()
    # Also add UserPlant row so get_user_scope reads it
    db.add(UserPlant(user_id=user.id, plant_name=plant))
    db.commit()
    db.refresh(user)
    return user


def _make_location(db: Session, plant: str, suffix: str = "") -> Location:
    loc_id = f"SC-LOC-{_uid()}{suffix}"
    now = datetime.utcnow()
    loc = Location(
        location_id=loc_id,
        location_name=f"Scope Location {loc_id}",
        qr_code=loc_id,  # Required NOT NULL
        plant=plant,
        area="Test Area",
        department="Safety",
        status="Active",
        created_at=now,
        updated_at=now,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def _get_or_create_asset_type(db: Session) -> MasterAssetType:
    at = db.query(MasterAssetType).filter(MasterAssetType.is_active == True).first()
    if at:
        return at
    at = MasterAssetType(name=f"CO2-{_uid()}", is_active=True)
    db.add(at)
    db.commit()
    db.refresh(at)
    return at


def _get_or_create_capacity(db: Session) -> MasterCapacityType:
    cap = db.query(MasterCapacityType).filter(MasterCapacityType.is_active == True).first()
    if cap:
        return cap
    cap = MasterCapacityType(name=f"4.5kg-{_uid()}", is_active=True)
    db.add(cap)
    db.commit()
    db.refresh(cap)
    return cap


def _make_asset(db: Session, location: Location = None) -> Asset:
    at = _get_or_create_asset_type(db)
    cap = _get_or_create_capacity(db)
    asset_id = f"SC-AST-{_uid()}"
    now = datetime.utcnow()
    asset = Asset(
        asset_id=asset_id,
        serial_number=f"SN-{asset_id}",
        asset_type_id=at.id,
        capacity_id=cap.id,
        status="Active",
        barcode=asset_id,
        location_id=location.location_id if location else None,
        created_at=now,
        updated_at=now,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _auth(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def scoping_data():
    """Create two plants, two users, two locations, two assets once for the module."""
    db = SessionLocal()
    try:
        plant_a = f"PlantA-{_uid()}"
        plant_b = f"PlantB-{_uid()}"

        user_a = _make_user(db, plant_a)
        user_b = _make_user(db, plant_b)

        # Admin user (global scope)
        admin = db.query(User).filter(User.role == "ADMIN", User.status == "Active").first()

        loc_a = _make_location(db, plant_a)
        loc_b = _make_location(db, plant_b)

        asset_a = _make_asset(db, loc_a)
        asset_b = _make_asset(db, loc_b)

        yield {
            "user_a": user_a, "user_b": user_b, "admin": admin,
            "loc_a": loc_a, "loc_b": loc_b,
            "asset_a": asset_a, "asset_b": asset_b,
            "plant_a": plant_a, "plant_b": plant_b,
        }
    finally:
        db.close()


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestAssetListScoping:
    def test_user_a_sees_only_plant_a_assets(self, scoping_data):
        d = scoping_data
        resp = client.get("/api/assets", headers=_auth(d["user_a"]))
        assert resp.status_code == 200
        ids = [a["asset_id"] for a in resp.json()["data"]["items"]]
        assert d["asset_a"].asset_id in ids
        assert d["asset_b"].asset_id not in ids

    def test_user_b_sees_only_plant_b_assets(self, scoping_data):
        d = scoping_data
        resp = client.get("/api/assets", headers=_auth(d["user_b"]))
        assert resp.status_code == 200
        ids = [a["asset_id"] for a in resp.json()["data"]["items"]]
        assert d["asset_b"].asset_id in ids
        assert d["asset_a"].asset_id not in ids

    def test_admin_sees_both_assets(self, scoping_data):
        d = scoping_data
        if d["admin"] is None:
            pytest.skip("No ADMIN user in DB")
        resp = client.get("/api/assets", headers=_auth(d["admin"]))
        assert resp.status_code == 200
        ids = [a["asset_id"] for a in resp.json()["data"]["items"]]
        assert d["asset_a"].asset_id in ids
        assert d["asset_b"].asset_id in ids


class TestLocationListScoping:
    def test_user_a_sees_only_plant_a_locations(self, scoping_data):
        d = scoping_data
        resp = client.get("/api/locations", headers=_auth(d["user_a"]))
        assert resp.status_code == 200
        ids = [l["location_id"] for l in resp.json()["data"]["items"]]
        assert d["loc_a"].location_id in ids
        assert d["loc_b"].location_id not in ids

    def test_user_b_sees_only_plant_b_locations(self, scoping_data):
        d = scoping_data
        resp = client.get("/api/locations", headers=_auth(d["user_b"]))
        assert resp.status_code == 200
        ids = [l["location_id"] for l in resp.json()["data"]["items"]]
        assert d["loc_b"].location_id in ids
        assert d["loc_a"].location_id not in ids

    def test_admin_sees_all_locations(self, scoping_data):
        d = scoping_data
        if d["admin"] is None:
            pytest.skip("No ADMIN user in DB")
        resp = client.get("/api/locations", headers=_auth(d["admin"]))
        assert resp.status_code == 200
        ids = [l["location_id"] for l in resp.json()["data"]["items"]]
        assert d["loc_a"].location_id in ids
        assert d["loc_b"].location_id in ids


class TestCrossPlan404:
    def test_user_a_gets_404_for_plant_b_asset(self, scoping_data):
        d = scoping_data
        resp = client.get(f"/api/assets/{d['asset_b'].asset_id}", headers=_auth(d["user_a"]))
        # Must be 404, not 403 (avoid leaking record existence)
        assert resp.status_code == 404

    def test_user_b_gets_404_for_plant_a_asset(self, scoping_data):
        d = scoping_data
        resp = client.get(f"/api/assets/{d['asset_a'].asset_id}", headers=_auth(d["user_b"]))
        assert resp.status_code == 404

    def test_user_a_gets_404_for_plant_b_location(self, scoping_data):
        d = scoping_data
        resp = client.get(f"/api/locations/{d['loc_b'].location_id}", headers=_auth(d["user_a"]))
        assert resp.status_code == 404

    def test_user_b_gets_404_for_plant_a_location(self, scoping_data):
        d = scoping_data
        resp = client.get(f"/api/locations/{d['loc_a'].location_id}", headers=_auth(d["user_b"]))
        assert resp.status_code == 404


class TestNoPlantFailClosed:
    def test_user_with_no_plant_gets_empty_assets(self):
        db = SessionLocal()
        try:
            uid = _uid()
            no_plant_user = User(
                employee_id=f"NP_{uid}",
                name=f"No Plant User {uid}",
                email=f"noplant_{uid}@test.com",
                password_hash=get_password_hash("NoPlant123!"),
                role="SAFETY OFFICER",
                department="Safety",
                plant=None,
                status="Active",
                is_first_login=False,
            )
            db.add(no_plant_user)
            db.commit()
            db.refresh(no_plant_user)
            user_id = no_plant_user.id
        finally:
            db.close()

        headers = _auth(no_plant_user)
        resp = client.get("/api/assets", headers=headers)
        assert resp.status_code == 200
        # Fail-closed: empty results
        assert resp.json()["data"]["items"] == []

    def test_user_with_no_plant_gets_empty_locations(self):
        db = SessionLocal()
        try:
            uid = _uid()
            no_plant_user = User(
                employee_id=f"NP2_{uid}",
                name=f"No Plant User2 {uid}",
                email=f"noplant2_{uid}@test.com",
                password_hash=get_password_hash("NoPlant123!"),
                role="SAFETY OFFICER",
                department="Safety",
                plant=None,
                status="Active",
                is_first_login=False,
            )
            db.add(no_plant_user)
            db.commit()
            db.refresh(no_plant_user)
        finally:
            db.close()

        headers = _auth(no_plant_user)
        resp = client.get("/api/locations", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["items"] == []


class TestDashboardScoping:
    def test_dashboard_stats_accessible(self, scoping_data):
        d = scoping_data
        resp = client.get("/api/dashboard/stats", headers=_auth(d["user_a"]))
        assert resp.status_code == 200
        body = resp.json()
        # Should have integer fields
        assert isinstance(body.get("total_assets"), int)
        assert isinstance(body.get("total_locations"), int)

    def test_dashboard_stats_admin_accessible(self, scoping_data):
        d = scoping_data
        if d["admin"] is None:
            pytest.skip("No ADMIN user in DB")
        resp = client.get("/api/dashboard/stats", headers=_auth(d["admin"]))
        assert resp.status_code == 200

    def test_asset_type_distribution_accessible(self, scoping_data):
        d = scoping_data
        resp = client.get("/api/dashboard/asset-type-distribution", headers=_auth(d["user_a"]))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_inspection_status_distribution_accessible(self, scoping_data):
        d = scoping_data
        resp = client.get("/api/dashboard/inspection-status-distribution", headers=_auth(d["user_a"]))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
