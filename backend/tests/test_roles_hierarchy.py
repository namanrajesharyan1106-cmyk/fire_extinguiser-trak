"""
Phase 3 — User Management & Role Hierarchy Tests
==================================================
Tests:
- Rank checks: ADMIN(100) > IT ADMIN(80) > SAFETY HEAD(60) > SAFETY OFFICER(50) > INSPECTOR(30) == MAINTENANCE(30) > VIEWER(10)
- Prevent users from creating/editing/resetting/deactivating users with role >= their own rank
- Block IT ADMIN from modifying their own role
- Prevent deactivating or demoting the last active ADMIN
- Plant and department validation against master tables & creator's scope
- Scoped GET /api/auth/users
- Token invalidation on role change, plant reassignment, or deactivation
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
from app.models.system import MasterPlant, MasterDepartment
from app.models.auth import RefreshToken
from app.services import auth_service

client = TestClient(app)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _get_or_create_plant(db: Session, name: str) -> MasterPlant:
    p = db.query(MasterPlant).filter(MasterPlant.name == name).first()
    if not p:
        p = MasterPlant(name=name, is_active=True)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def _get_or_create_dept(db: Session, name: str) -> MasterDepartment:
    d = db.query(MasterDepartment).filter(MasterDepartment.name == name).first()
    if not d:
        d = MasterDepartment(name=name, is_active=True)
        db.add(d)
        db.commit()
        db.refresh(d)
    return d


class UserInfo:
    def __init__(self, user_id: int, email: str, role: str, plant: str):
        self.id = user_id
        self.email = email
        self.role = role
        self.plant = plant


def _create_user(db: Session, role: str, plant: str = "PlantA", is_first_login: bool = False) -> UserInfo:
    uid = _uid()
    _get_or_create_plant(db, plant)
    _get_or_create_dept(db, "Safety")
    u = User(
        employee_id=f"EMP_{uid}",
        name=f"User {uid}",
        email=f"user_{uid}@test.com",
        password_hash=get_password_hash("Password123!"),
        role=role,
        department="Safety",
        plant=plant,
        status="Active",
        is_first_login=is_first_login,
        created_at=datetime.utcnow(),
    )
    db.add(u)
    db.flush()
    db.add(UserPlant(user_id=u.id, plant_name=plant))
    db.commit()
    return UserInfo(user_id=u.id, email=u.email, role=u.role, plant=u.plant)


def _auth(user: UserInfo) -> dict:
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


class TestRoleHierarchyCreation:
    def test_it_admin_cannot_create_admin(self):
        db = SessionLocal()
        try:
            it_admin = _create_user(db, "IT ADMIN")
        finally:
            db.close()

        headers = _auth(it_admin)
        resp = client.post(
            "/api/auth/users",
            headers=headers,
            json={
                "employee_id": f"ADM_{_uid()}",
                "name": "Target Admin",
                "email": f"adm_{_uid()}@test.com",
                "password": "Password123!",
                "role": "ADMIN",
                "plant": "PlantA",
                "department": "Safety",
            },
        )
        assert resp.status_code == 403

    def test_it_admin_cannot_create_it_admin(self):
        db = SessionLocal()
        try:
            it_admin = _create_user(db, "IT ADMIN")
        finally:
            db.close()

        headers = _auth(it_admin)
        resp = client.post(
            "/api/auth/users",
            headers=headers,
            json={
                "employee_id": f"IT_{_uid()}",
                "name": "Target IT Admin",
                "email": f"it_{_uid()}@test.com",
                "password": "Password123!",
                "role": "IT ADMIN",
                "plant": "PlantA",
                "department": "Safety",
            },
        )
        assert resp.status_code == 403

    def test_it_admin_can_create_safety_officer(self):
        db = SessionLocal()
        try:
            it_admin = _create_user(db, "IT ADMIN")
        finally:
            db.close()

        headers = _auth(it_admin)
        resp = client.post(
            "/api/auth/users",
            headers=headers,
            json={
                "employee_id": f"SO_{_uid()}",
                "name": "Target Safety Officer",
                "email": f"so_{_uid()}@test.com",
                "password": "Password123!",
                "role": "SAFETY OFFICER",
                "plant": "PlantA",
                "department": "Safety",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["role"] == "SAFETY OFFICER"


class TestRoleHierarchyModification:
    def test_it_admin_cannot_edit_admin(self):
        db = SessionLocal()
        try:
            it_admin = _create_user(db, "IT ADMIN")
            admin_user = _create_user(db, "ADMIN")
        finally:
            db.close()

        headers = _auth(it_admin)
        resp = client.put(
            f"/api/auth/users/{admin_user.id}",
            headers=headers,
            json={"name": "Hacked Admin"},
        )
        assert resp.status_code == 403

    def test_it_admin_cannot_modify_own_role(self):
        db = SessionLocal()
        try:
            it_admin = _create_user(db, "IT ADMIN")
        finally:
            db.close()

        headers = _auth(it_admin)
        resp = client.put(
            f"/api/auth/users/{it_admin.id}",
            headers=headers,
            json={"role": "ADMIN"},
        )
        assert resp.status_code == 403

    def test_it_admin_cannot_promote_to_admin(self):
        db = SessionLocal()
        try:
            it_admin = _create_user(db, "IT ADMIN")
            so_user = _create_user(db, "SAFETY OFFICER")
        finally:
            db.close()

        headers = _auth(it_admin)
        resp = client.put(
            f"/api/auth/users/{so_user.id}",
            headers=headers,
            json={"role": "ADMIN"},
        )
        assert resp.status_code == 403

    def test_last_admin_protection(self):
        db = SessionLocal()
        try:
            # Demote all existing admins except one
            admins = db.query(User).filter(User.role == "ADMIN", User.status == "Active").all()
            if not admins:
                admin_obj = _create_user(db, "ADMIN")
                admin_id = admin_obj.id
            else:
                admin_id = admins[0].id
                for other in admins[1:]:
                    other.status = "Inactive"
                db.commit()
        finally:
            db.close()

        admin_info = UserInfo(user_id=admin_id, email="admin@test.com", role="ADMIN", plant="PlantA")
        headers = _auth(admin_info)
        # Try demoting the last admin
        resp = client.put(
            f"/api/auth/users/{admin_id}",
            headers=headers,
            json={"role": "VIEWER"},
        )
        assert resp.status_code == 400
        assert "last active Administrator" in resp.json()["message"]


class TestUserScopingAndTokens:
    def test_users_list_scoped_by_plant(self):
        db = SessionLocal()
        try:
            plant_x = f"PlantX-{_uid()}"
            plant_y = f"PlantY-{_uid()}"
            user_x = _create_user(db, "IT ADMIN", plant=plant_x)
            user_y = _create_user(db, "SAFETY OFFICER", plant=plant_y)
        finally:
            db.close()

        headers = _auth(user_x)
        resp = client.get("/api/auth/users", headers=headers)
        assert resp.status_code == 200
        emails = [u["email"] for u in resp.json()["data"]]
        assert user_x.email in emails
        assert user_y.email not in emails

    def test_token_revoked_on_role_change(self):
        db = SessionLocal()
        try:
            admin_obj = db.query(User).filter(User.role == "ADMIN", User.status == "Active").first()
            if not admin_obj:
                admin = _create_user(db, "ADMIN")
            else:
                admin = UserInfo(user_id=admin_obj.id, email=admin_obj.email, role=admin_obj.role, plant=admin_obj.plant)
            target = _create_user(db, "VIEWER")

            # Create refresh token for target using auth_service
            raw_token = auth_service.create_refresh_token(db, target.id)
            rf = db.query(RefreshToken).filter(RefreshToken.user_id == target.id, RefreshToken.is_revoked == False).first()
            rf_id = rf.id
        finally:
            db.close()

        headers = _auth(admin)
        resp = client.put(
            f"/api/auth/users/{target.id}",
            headers=headers,
            json={"role": "INSPECTOR"},
        )
        assert resp.status_code == 200

        # Verify token was revoked
        db = SessionLocal()
        try:
            updated_rf = db.query(RefreshToken).filter(RefreshToken.id == rf_id).first()
            assert updated_rf.is_revoked is True
        finally:
            db.close()

    def test_invalid_plant_rejected(self):
        db = SessionLocal()
        try:
            admin_obj = db.query(User).filter(User.role == "ADMIN", User.status == "Active").first()
            if not admin_obj:
                admin = _create_user(db, "ADMIN")
            else:
                admin = UserInfo(user_id=admin_obj.id, email=admin_obj.email, role=admin_obj.role, plant=admin_obj.plant)
        finally:
            db.close()

        headers = _auth(admin)
        resp = client.post(
            "/api/auth/users",
            headers=headers,
            json={
                "employee_id": f"INV_{_uid()}",
                "name": "Invalid Plant User",
                "email": f"inv_{_uid()}@test.com",
                "password": "Password123!",
                "role": "VIEWER",
                "plant": "NonExistentPlant12345",
                "department": "Safety",
            },
        )
        assert resp.status_code == 400
        assert "Invalid plant" in resp.json()["message"]
