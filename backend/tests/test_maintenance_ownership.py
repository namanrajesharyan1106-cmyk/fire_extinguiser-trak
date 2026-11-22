"""
Tests for Phase 4: Maintenance & Inspection Ownership, Separation of Duties, and Image Validation.
"""

import io
import uuid
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.core.database import SessionLocal
from app import models
from app.core import security

client = TestClient(app)


class TestFixture:
    def __init__(self):
        self.db = SessionLocal()
        uid = uuid.uuid4().hex[:8]

        # Plants
        self.plant_a = f"P4A_{uid}"
        self.plant_b = f"P4B_{uid}"
        self.db.add(models.MasterPlant(name=self.plant_a, is_active=True))
        self.db.add(models.MasterPlant(name=self.plant_b, is_active=True))

        # Locations
        self.loc_a_id = f"LOC-A-{uid}"
        self.loc_b_id = f"LOC-B-{uid}"
        self.loc_a = models.Location(
            location_id=self.loc_a_id,
            location_name=f"Location A {uid}",
            plant=self.plant_a,
            department="Maintenance",
            qr_code=f"QR-A-{uid}",
            status="Active",
        )
        self.loc_b = models.Location(
            location_id=self.loc_b_id,
            location_name=f"Location B {uid}",
            plant=self.plant_b,
            department="Maintenance",
            qr_code=f"QR-B-{uid}",
            status="Active",
        )
        self.db.add(self.loc_a)
        self.db.add(self.loc_b)

        # Assets
        self.asset_a_id = f"AST-A-{uid}"
        self.asset_b_id = f"AST-B-{uid}"
        self.asset_a = models.Asset(
            asset_id=self.asset_a_id,
            serial_number=f"SN-A-{uid}",
            location_id=self.loc_a_id,
            status="Active",
        )
        self.asset_b = models.Asset(
            asset_id=self.asset_b_id,
            serial_number=f"SN-B-{uid}",
            location_id=self.loc_b_id,
            status="Active",
        )
        self.db.add(self.asset_a)
        self.db.add(self.asset_b)

        # Users
        pw_hash = security.get_password_hash("ValidPass123!@#")
        
        self.admin = models.User(
            employee_id=f"ADM_{uid}",
            name=f"Admin {uid}",
            email=f"admin_{uid}@test.com",
            password_hash=pw_hash,
            role="ADMIN",
            status="Active",
            plant=self.plant_a,
        )
        self.safety_officer = models.User(
            employee_id=f"SO_{uid}",
            name=f"SafetyOfficer {uid}",
            email=f"so_{uid}@test.com",
            password_hash=pw_hash,
            role="SAFETY OFFICER",
            status="Active",
            plant=self.plant_a,
            department="Maintenance",
        )
        self.tech_1 = models.User(
            employee_id=f"T1_{uid}",
            name=f"Tech1 {uid}",
            email=f"tech1_{uid}@test.com",
            password_hash=pw_hash,
            role="MAINTENANCE",
            status="Active",
            plant=self.plant_a,
            department="Maintenance",
        )
        self.tech_2 = models.User(
            employee_id=f"T2_{uid}",
            name=f"Tech2 {uid}",
            email=f"tech2_{uid}@test.com",
            password_hash=pw_hash,
            role="MAINTENANCE",
            status="Active",
            plant=self.plant_a,
            department="Maintenance",
        )
        self.tech_b = models.User(
            employee_id=f"TB_{uid}",
            name=f"TechB {uid}",
            email=f"techb_{uid}@test.com",
            password_hash=pw_hash,
            role="MAINTENANCE",
            status="Active",
            plant=self.plant_b,
            department="Maintenance",
        )
        self.inspector = models.User(
            employee_id=f"INS_{uid}",
            name=f"Inspector {uid}",
            email=f"ins_{uid}@test.com",
            password_hash=pw_hash,
            role="INSPECTOR",
            status="Active",
            plant=self.plant_a,
            department="Maintenance",
        )

        self.db.add_all([
            self.admin, self.safety_officer, self.tech_1, self.tech_2, self.tech_b, self.inspector
        ])
        self.db.commit()

        # Extract IDs
        self.admin_id = self.admin.id
        self.admin_name = self.admin.name
        self.so_id = self.safety_officer.id
        self.t1_id = self.tech_1.id
        self.t2_id = self.tech_2.id
        self.tb_id = self.tech_b.id
        self.ins_id = self.inspector.id
        self.ins_name = self.inspector.name

        self.admin_token = security.create_access_token({"sub": str(self.admin_id), "type": "access"})
        self.so_token = security.create_access_token({"sub": str(self.so_id), "type": "access"})
        self.t1_token = security.create_access_token({"sub": str(self.t1_id), "type": "access"})
        self.t2_token = security.create_access_token({"sub": str(self.t2_id), "type": "access"})
        self.tb_token = security.create_access_token({"sub": str(self.tb_id), "type": "access"})
        self.ins_token = security.create_access_token({"sub": str(self.ins_id), "type": "access"})

        self.db.close()

    def get_headers(self, token: str):
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def fix():
    return TestFixture()


def test_technician_ticket_visibility(fix):
    """
    MAINTENANCE role can view:
    - Tickets assigned to them
    - Tickets in scope that are unassigned
    CANNOT view:
    - Tickets assigned to other technicians
    """
    db = SessionLocal()
    # Create ticket assigned to tech 1
    t1_ticket = models.Maintenance(
        asset_id=fix.asset_a_id,
        location_id=fix.loc_a_id,
        issue="T1 issue",
        status="Open",
        technician_id=fix.t1_id,
        opened_date=datetime.utcnow(),
    )
    # Create ticket unassigned in Plant A
    unassigned_ticket = models.Maintenance(
        asset_id=fix.asset_a_id,
        location_id=fix.loc_a_id,
        issue="Unassigned issue",
        status="Open",
        technician_id=None,
        opened_date=datetime.utcnow(),
    )
    # Create ticket assigned to tech 2
    t2_ticket = models.Maintenance(
        asset_id=fix.asset_a_id,
        location_id=fix.loc_a_id,
        issue="T2 issue",
        status="Open",
        technician_id=fix.t2_id,
        opened_date=datetime.utcnow(),
    )
    db.add_all([t1_ticket, unassigned_ticket, t2_ticket])
    db.commit()
    t1_tid = t1_ticket.maintenance_id
    unassigned_tid = unassigned_ticket.maintenance_id
    t2_tid = t2_ticket.maintenance_id
    db.close()

    # Tech 1 requests ticket list
    r = client.get("/api/maintenance", headers=fix.get_headers(fix.t1_token))
    assert r.status_code == 200
    tids = [t["maintenance_id"] for t in r.json()["data"]]
    assert t1_tid in tids
    assert unassigned_tid in tids
    assert t2_tid not in tids

    # Tech 1 gets own ticket -> 200
    r = client.get(f"/api/maintenance/{t1_tid}", headers=fix.get_headers(fix.t1_token))
    assert r.status_code == 200

    # Tech 1 gets unassigned ticket -> 200
    r = client.get(f"/api/maintenance/{unassigned_tid}", headers=fix.get_headers(fix.t1_token))
    assert r.status_code == 200

    # Tech 1 gets tech 2's ticket -> 404 (hidden)
    r = client.get(f"/api/maintenance/{t2_tid}", headers=fix.get_headers(fix.t1_token))
    assert r.status_code == 404


def test_technician_cannot_update_unassigned_or_others_ticket(fix):
    """
    MAINTENANCE role can update only tickets where technician_id == current_user.id.
    Unassigned tickets in scope are view-only for technicians.
    """
    db = SessionLocal()
    unassigned = models.Maintenance(
        asset_id=fix.asset_a_id,
        location_id=fix.loc_a_id,
        issue="Unassigned issue",
        status="Open",
        technician_id=None,
        opened_date=datetime.utcnow(),
    )
    db.add(unassigned)
    db.commit()
    unassigned_id = unassigned.maintenance_id
    db.close()

    # Tech 1 tries to update unassigned ticket -> 403
    r = client.put(
        f"/api/maintenance/{unassigned_id}",
        json={"remarks": "Tech attempting update on unassigned"},
        headers=fix.get_headers(fix.t1_token),
    )
    assert r.status_code == 403

    # Tech 1 tries to update status of unassigned ticket -> 403
    r = client.put(
        f"/api/maintenance/{unassigned_id}/status",
        json={"new_status": "In Progress"},
        headers=fix.get_headers(fix.t1_token),
    )
    assert r.status_code == 403


def test_technician_cannot_change_technician_id(fix):
    """
    Technician cannot change technician_id assignment.
    """
    db = SessionLocal()
    ticket = models.Maintenance(
        asset_id=fix.asset_a_id,
        location_id=fix.loc_a_id,
        issue="T1 issue",
        status="Open",
        technician_id=fix.t1_id,
        opened_date=datetime.utcnow(),
    )
    db.add(ticket)
    db.commit()
    tid = ticket.maintenance_id
    db.close()

    # Tech 1 tries to reassign to Tech 2 -> 403
    r = client.put(
        f"/api/maintenance/{tid}",
        json={"technician_id": fix.t2_id},
        headers=fix.get_headers(fix.t1_token),
    )
    assert r.status_code == 403

    r = client.put(
        f"/api/maintenance/{tid}/status",
        json={"new_status": "In Progress", "technician_id": fix.t2_id},
        headers=fix.get_headers(fix.t1_token),
    )
    assert r.status_code == 403


def test_technician_assignment_plant_validation(fix):
    """
    Assigned technician must belong to the ticket's plant.
    Safety Officer of Plant A cannot assign Tech B (Plant B) to Plant A's ticket.
    """
    db = SessionLocal()
    ticket = models.Maintenance(
        asset_id=fix.asset_a_id,
        location_id=fix.loc_a_id,
        issue="Needs tech",
        status="Open",
        opened_date=datetime.utcnow(),
    )
    db.add(ticket)
    db.commit()
    tid = ticket.maintenance_id
    db.close()

    # Assigning Tech B (from Plant B) to Plant A ticket -> 400
    r = client.put(
        f"/api/maintenance/{tid}",
        json={"technician_id": fix.tb_id},
        headers=fix.get_headers(fix.so_token),
    )
    assert r.status_code == 400
    assert "Technician does not belong to ticket's plant" in r.text

    # Assigning Tech 1 (from Plant A) to Plant A ticket -> 200
    r = client.put(
        f"/api/maintenance/{tid}",
        json={"technician_id": fix.t1_id},
        headers=fix.get_headers(fix.so_token),
    )
    assert r.status_code == 200
    assert r.json()["data"]["technician_id"] == fix.t1_id


def test_separation_of_duties_completed_cannot_verify(fix):
    """
    Separation of duties: The user who moved a ticket to "Completed" cannot also "Verify" it.
    """
    db = SessionLocal()
    ticket = models.Maintenance(
        asset_id=fix.asset_a_id,
        location_id=fix.loc_a_id,
        issue="Separation test",
        status="In Progress",
        technician_id=fix.so_id,  # Safety Officer assigned as tech for test
        opened_date=datetime.utcnow(),
    )
    db.add(ticket)
    db.commit()
    tid = ticket.maintenance_id
    db.close()

    # Safety Officer completes the ticket
    r = client.put(
        f"/api/maintenance/{tid}/status",
        json={"new_status": "Completed"},
        headers=fix.get_headers(fix.so_token),
    )
    assert r.status_code == 200
    assert r.json()["data"]["completed_by_id"] == fix.so_id

    # Safety Officer tries to verify the ticket they completed -> 400
    r = client.put(
        f"/api/maintenance/{tid}/status",
        json={"new_status": "Verified"},
        headers=fix.get_headers(fix.so_token),
    )
    assert r.status_code == 400
    assert "user who completed the maintenance ticket cannot verify it" in r.text

    # Another user with verify permission (ADMIN) verifies the ticket -> 200
    r = client.put(
        f"/api/maintenance/{tid}/status",
        json={"new_status": "Verified", "verified_by": "spoofed_name"},
        headers=fix.get_headers(fix.admin_token),
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "Verified"
    # verified_by must be set to current_user.id server-side, ignoring spoofed_name
    assert data["verified_by"] == str(fix.admin_id)


def test_inspector_scope_and_display_name_enforcement(fix):
    """
    Inspector:
    - Can only create inspections for assets/locations in scope (Plant A)
    - Creating for Plant B asset/location returns 404
    - Display name inspector must be taken from current_user.name, ignoring client payload
    """
    # 1. Inspector creates inspection for Plant B location -> 404
    r = client.post(
        "/api/inspections",
        json={
            "location_id": fix.loc_b_id,
            "asset_id": fix.asset_b_id,
            "pressure": "Pass",
            "seal": "Pass",
            "pin": "Pass",
            "gauge": "Pass",
            "hose": "Pass",
            "nozzle": "Pass",
            "visibility": "Pass",
            "accessibility": "Pass",
            "mounting": "Pass",
            "safety_tag": "Pass",
            "cylinder_damage": "Pass",
            "inspector": "Spoofed Inspector",
        },
        headers=fix.get_headers(fix.ins_token),
    )
    assert r.status_code == 404

    # 2. Inspector creates inspection for Plant A location -> 201
    r = client.post(
        "/api/inspections",
        json={
            "location_id": fix.loc_a_id,
            "asset_id": fix.asset_a_id,
            "pressure": "Pass",
            "seal": "Pass",
            "pin": "Pass",
            "gauge": "Pass",
            "hose": "Pass",
            "nozzle": "Pass",
            "visibility": "Pass",
            "accessibility": "Pass",
            "mounting": "Pass",
            "safety_tag": "Pass",
            "cylinder_damage": "Pass",
            "inspector": "Spoofed Inspector",
        },
        headers=fix.get_headers(fix.ins_token),
    )
    assert r.status_code == 201
    data = r.json()["data"]
    # Verify inspector name is forced server-side to fix.ins_name
    assert data["inspector"] == fix.ins_name
    assert data["inspector_id"] == fix.ins_id


def test_photo_upload_validation_and_scope(fix):
    """
    Photo upload endpoints:
    - Scope check: cannot upload to out-of-scope record (404)
    - Validates real image content (Pillow verify)
    - Rejects non-image and corrupt files (400)
    - Enforces size limit
    """
    # Helper to generate test JPEG
    def make_test_image(format="JPEG", size=(50, 50)):
        buf = io.BytesIO()
        img = Image.new("RGB", size, color="blue")
        img.save(buf, format=format)
        buf.seek(0)
        return buf.getvalue()

    valid_jpeg = make_test_image("JPEG")
    corrupt_bytes = b"NOT_AN_IMAGE_FILE_JUST_PLAIN_TEXT"

    # 1. Asset photo upload: Out of scope -> 404
    r = client.post(
        f"/api/assets/{fix.asset_b_id}/photo",
        files={"file": ("photo.jpg", valid_jpeg, "image/jpeg")},
        headers=fix.get_headers(fix.so_token),
    )
    assert r.status_code == 404

    # 2. Asset photo upload: Corrupt content -> 400
    r = client.post(
        f"/api/assets/{fix.asset_a_id}/photo",
        files={"file": ("photo.jpg", corrupt_bytes, "image/jpeg")},
        headers=fix.get_headers(fix.so_token),
    )
    assert r.status_code == 400
    assert "Invalid image" in r.text or "corrupt" in r.text

    # 3. Asset photo upload: Valid JPEG -> 200
    r = client.post(
        f"/api/assets/{fix.asset_a_id}/photo",
        files={"file": ("photo.jpg", valid_jpeg, "image/jpeg")},
        headers=fix.get_headers(fix.so_token),
    )
    assert r.status_code == 200
    assert "uploads/photos/" in r.json()["data"]["photo_url"]

    # 4. Maintenance photo upload: Tech cannot upload to other tech's ticket -> 403
    db = SessionLocal()
    t2_ticket = models.Maintenance(
        asset_id=fix.asset_a_id,
        location_id=fix.loc_a_id,
        issue="Tech 2 ticket",
        status="Open",
        technician_id=fix.t2_id,
        opened_date=datetime.utcnow(),
    )
    db.add(t2_ticket)
    db.commit()
    t2_tid = t2_ticket.maintenance_id
    db.close()

    r = client.post(
        f"/api/maintenance/{t2_tid}/photos",
        files={"file": ("evidence.jpg", valid_jpeg, "image/jpeg")},
        headers=fix.get_headers(fix.t1_token),
    )
    assert r.status_code == 403

    # 5. Maintenance photo upload: Tech 2 uploads to own ticket -> 200
    r = client.post(
        f"/api/maintenance/{t2_tid}/photos",
        files={"file": ("evidence.jpg", valid_jpeg, "image/jpeg")},
        headers=fix.get_headers(fix.t2_token),
    )
    assert r.status_code == 200
    assert "uploads/photos/" in r.json()["data"]["file_path"]
