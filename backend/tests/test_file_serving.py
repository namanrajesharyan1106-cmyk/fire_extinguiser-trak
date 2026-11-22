"""
Tests for Phase 5: Secure File Serving, Scoping, and Security Headers.
"""

import os
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app import models
from app.core import security

client = TestClient(app)


class FileTestFixture:
    def __init__(self):
        self.db = SessionLocal()
        uid = uuid.uuid4().hex[:8]

        # Plants
        self.plant_a = f"F5A_{uid}"
        self.plant_b = f"F5B_{uid}"
        self.db.add(models.MasterPlant(name=self.plant_a, is_active=True))
        self.db.add(models.MasterPlant(name=self.plant_b, is_active=True))

        # Locations
        self.loc_a_id = f"LOC-FA-{uid}"
        self.loc_b_id = f"LOC-FB-{uid}"
        self.loc_a = models.Location(
            location_id=self.loc_a_id,
            location_name=f"Location FA {uid}",
            plant=self.plant_a,
            department="Operations",
            qr_code=f"QR-FA-{uid}",
            status="Active",
        )
        self.loc_b = models.Location(
            location_id=self.loc_b_id,
            location_name=f"Location FB {uid}",
            plant=self.plant_b,
            department="Operations",
            qr_code=f"QR-FB-{uid}",
            status="Active",
        )
        self.db.add(self.loc_a)
        self.db.add(self.loc_b)

        # Create dummy photo on disk with random UUID
        self.photo_filename_a = f"{uuid.uuid4().hex}.jpg"
        photo_dir = os.path.join(settings.UPLOAD_DIR, "photos")
        os.makedirs(photo_dir, exist_ok=True)
        self.photo_path_a = os.path.join(photo_dir, self.photo_filename_a)
        with open(self.photo_path_a, "wb") as f:
            f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 50)  # minimal jpeg header bytes

        # Assets
        self.asset_a_id = f"AST-FA-{uid}"
        self.asset_a = models.Asset(
            asset_id=self.asset_a_id,
            serial_number=f"SN-FA-{uid}",
            location_id=self.loc_a_id,
            photo=f"uploads/photos/{self.photo_filename_a}",
            status="Active",
        )
        self.db.add(self.asset_a)

        # Maintenance ticket in Plant A with evidence attachment
        self.maint_filename_a = f"{uuid.uuid4().hex}.jpg"
        self.maint_path_a = os.path.join(photo_dir, self.maint_filename_a)
        with open(self.maint_path_a, "wb") as f:
            f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 50)

        # Users
        pw_hash = security.get_password_hash("ValidPass123!@#")
        self.admin = models.User(
            employee_id=f"ADM_{uid}",
            name=f"Admin {uid}",
            email=f"f5admin_{uid}@test.com",
            password_hash=pw_hash,
            role="ADMIN",
            status="Active",
        )
        self.user_a = models.User(
            employee_id=f"UA_{uid}",
            name=f"User A {uid}",
            email=f"f5ua_{uid}@test.com",
            password_hash=pw_hash,
            role="SAFETY OFFICER",
            status="Active",
            plant=self.plant_a,
        )
        self.user_b = models.User(
            employee_id=f"UB_{uid}",
            name=f"User B {uid}",
            email=f"f5ub_{uid}@test.com",
            password_hash=pw_hash,
            role="SAFETY OFFICER",
            status="Active",
            plant=self.plant_b,
        )
        self.tech_a = models.User(
            employee_id=f"TA_{uid}",
            name=f"Tech A {uid}",
            email=f"f5ta_{uid}@test.com",
            password_hash=pw_hash,
            role="MAINTENANCE",
            status="Active",
            plant=self.plant_a,
        )
        self.tech_a2 = models.User(
            employee_id=f"TA2_{uid}",
            name=f"Tech A2 {uid}",
            email=f"f5ta2_{uid}@test.com",
            password_hash=pw_hash,
            role="MAINTENANCE",
            status="Active",
            plant=self.plant_a,
        )
        self.db.add_all([self.admin, self.user_a, self.user_b, self.tech_a, self.tech_a2])
        self.db.commit()

        self.ticket_a = models.Maintenance(
            asset_id=self.asset_a_id,
            location_id=self.loc_a_id,
            issue="Test ticket",
            status="Open",
            technician_id=self.tech_a.id,
        )
        self.db.add(self.ticket_a)
        self.db.commit()

        self.attachment_a = models.Attachment(
            related_id=str(self.ticket_a.maintenance_id),
            related_type="maintenance",
            file_path=f"uploads/photos/{self.maint_filename_a}",
            file_type="image/jpeg",
            label="Ticket Evidence",
            uploaded_by=self.user_a.id,
        )
        self.db.add(self.attachment_a)
        self.db.commit()

        self.admin_id = self.admin.id
        self.user_a_id = self.user_a.id
        self.user_b_id = self.user_b.id
        self.tech_a_id = self.tech_a.id
        self.tech_a2_id = self.tech_a2.id

        self.admin_token = security.create_access_token({"sub": str(self.admin_id), "type": "access"})
        self.user_a_token = security.create_access_token({"sub": str(self.user_a_id), "type": "access"})
        self.user_b_token = security.create_access_token({"sub": str(self.user_b_id), "type": "access"})
        self.tech_a_token = security.create_access_token({"sub": str(self.tech_a_id), "type": "access"})
        self.tech_a2_token = security.create_access_token({"sub": str(self.tech_a2_id), "type": "access"})

        self.db.close()

    def get_headers(self, token: str):
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def fix():
    return FileTestFixture()


def test_uploads_static_mount_removed(fix):
    """
    Direct access to /uploads/... must return 404 (static mount removed).
    """
    r = client.get(f"/uploads/photos/{fix.photo_filename_a}")
    assert r.status_code == 404


def test_unauthenticated_file_access_blocked(fix):
    """
    Unauthenticated access to /api/files/... must return 401.
    """
    r = client.get(f"/api/files/photos/{fix.photo_filename_a}")
    assert r.status_code == 401


def test_asset_photo_scoping_and_headers(fix):
    """
    Asset photo file access:
    - User in Plant A: 200 + security headers
    - User in Plant B: 404
    - Admin: 200
    """
    # User A (Plant A) -> 200
    r = client.get(
        f"/api/files/photos/{fix.photo_filename_a}",
        headers=fix.get_headers(fix.user_a_token),
    )
    assert r.status_code == 200
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert "private" in r.headers.get("cache-control", "")
    assert "inline" in r.headers.get("content-disposition", "")
    assert r.headers.get("content-type") == "image/jpeg"

    # User B (Plant B) -> 404
    r = client.get(
        f"/api/files/photos/{fix.photo_filename_a}",
        headers=fix.get_headers(fix.user_b_token),
    )
    assert r.status_code == 404

    # Admin -> 200
    r = client.get(
        f"/api/files/photos/{fix.photo_filename_a}",
        headers=fix.get_headers(fix.admin_token),
    )
    assert r.status_code == 200


def test_maintenance_evidence_scoping(fix):
    """
    Maintenance evidence photo:
    - User A (Plant A): 200
    - User B (Plant B): 404
    - Assigned Tech A: 200
    - Other Tech A2 (not assigned): 404
    """
    # User A (Plant A) -> 200
    r = client.get(
        f"/api/files/photos/{fix.maint_filename_a}",
        headers=fix.get_headers(fix.user_a_token),
    )
    assert r.status_code == 200

    # User B (Plant B) -> 404
    r = client.get(
        f"/api/files/photos/{fix.maint_filename_a}",
        headers=fix.get_headers(fix.user_b_token),
    )
    assert r.status_code == 404

    # Assigned Tech A -> 200
    r = client.get(
        f"/api/files/photos/{fix.maint_filename_a}",
        headers=fix.get_headers(fix.tech_a_token),
    )
    assert r.status_code == 200

    # Unassigned Tech A2 -> 404
    r = client.get(
        f"/api/files/photos/{fix.maint_filename_a}",
        headers=fix.get_headers(fix.tech_a2_token),
    )
    assert r.status_code == 404


def test_path_traversal_and_invalid_kind(fix):
    """
    Path traversal attempts and invalid file categories return 400.
    """
    # Invalid kind
    r = client.get(
        "/api/files/secrets/test.jpg",
        headers=fix.get_headers(fix.admin_token),
    )
    assert r.status_code == 400

    # Path traversal (should be blocked with 400 or 404 by router)
    r = client.get(
        "/api/files/photos/..%2F..%2Fetc%2Fpasswd",
        headers=fix.get_headers(fix.admin_token),
    )
    assert r.status_code in [400, 404]
