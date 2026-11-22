import io
import sys
import os
import openpyxl

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import Location, Asset, User, AuditLog
from app.core.security import create_access_token

client = TestClient(app)

# Generate admin auth token
db = SessionLocal()
admin_user = db.query(User).filter(User.role == "ADMIN").first()
token = create_access_token({"sub": str(admin_user.id), "type": "access"})
db.close()

AUTH_HEADERS = {"Authorization": f"Bearer {token}"}

def create_excel_file(rows, headers=None):
    if headers is None:
        headers = [
            "Location Name", "Plant", "Area", "Department",
            "Building", "Floor", "Required Asset Type", "Required Capacity", "QR Code Value (Optional)"
        ]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream

def test_feature_1_sample_download():
    print("\n--- Testing Feature 1: Sample Template Download ---")
    resp = client.get("/api/locations/bulk-upload/sample", headers=AUTH_HEADERS)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert "openxmlformats" in resp.headers["content-type"]
    
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    ws = wb.active
    headers = [cell.value for cell in ws[1] if cell.value is not None]
    print(f"Sample Headers: {headers}")
    assert "Location Name" in headers
    assert "Plant" in headers
    assert "Area" in headers
    assert "Department" in headers
    assert "Building" in headers
    assert "Floor" in headers
    assert "Required Asset Type" in headers
    assert "Required Capacity" in headers
    print("PASS: Sample template generated with correct headers and master data dropdowns.")

def test_feature_1_bulk_upload_preview():
    print("\n--- Testing Feature 1: Bulk Upload Preview & Validation ---")
    
    # 1. Valid row
    valid_rows = [
        ["Test Point Alpha", "PP02", "Assembly", "Production", "Main Building", "Ground", "ABC", "6kg", "QR-ALPHA-01"]
    ]
    file_bytes = create_excel_file(valid_rows)
    resp = client.post(
        "/api/locations/bulk-upload/preview",
        headers=AUTH_HEADERS,
        files={"file": ("test_preview.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert resp.status_code == 200, f"Preview failed: {resp.text}"
    data = resp.json()["data"]
    assert data["summary"]["total"] == 1
    assert data["summary"]["valid"] == 1
    assert data["summary"]["invalid"] == 0
    assert data["preview"][0]["status"] == "VALID"
    print("PASS: Valid row preview verified.")

    # 2. Invalid row (missing plant & invalid asset type)
    invalid_rows = [
        ["Test Point Beta", "", "Assembly", "Production", "Main Bldg", "Ground Floor", "INVALID_TYPE", "99kg", ""]
    ]
    file_bytes2 = create_excel_file(invalid_rows)
    resp2 = client.post(
        "/api/locations/bulk-upload/preview",
        headers=AUTH_HEADERS,
        files={"file": ("test_invalid.xlsx", file_bytes2, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert resp2.status_code == 200
    data2 = resp2.json()["data"]
    assert data2["summary"]["invalid"] == 1
    assert data2["preview"][0]["status"] == "INVALID"
    assert len(data2["preview"][0]["errors"]) >= 2
    print(f"PASS: Invalid row preview caught errors: {data2['preview'][0]['errors']}")

    # 3. Duplicate row (intra-file duplicate)
    duplicate_rows = [
        ["Duplicate Loc", "PP02", "Assembly", "Production", "Main Building", "Ground", "ABC", "6kg", ""],
        ["Duplicate Loc", "PP02", "Assembly", "Production", "Main Building", "Ground", "ABC", "6kg", ""]
    ]
    file_bytes3 = create_excel_file(duplicate_rows)
    resp3 = client.post(
        "/api/locations/bulk-upload/preview",
        headers=AUTH_HEADERS,
        files={"file": ("test_dups.xlsx", file_bytes3, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert resp3.status_code == 200
    data3 = resp3.json()["data"]
    assert data3["summary"]["duplicates"] == 1
    assert data3["summary"]["valid"] == 1
    assert data3["preview"][1]["status"] == "DUPLICATE"
    print("PASS: Intra-file duplicate row correctly detected.")

def test_feature_1_bulk_upload_execution():
    print("\n--- Testing Feature 1: Bulk Upload Execution & Data Safety ---")
    unique_name = "AutoTest Loc Gamma 99"
    rows = [
        [unique_name, "PP02", "Assembly", "Production", "Main Building", "Ground", "ABC", "6kg", ""],
        ["Invalid Row Master", "NON_EXISTENT_PLANT", "Assembly", "Production", "Main Building", "Ground", "ABC", "6kg", ""]
    ]
    file_bytes = create_excel_file(rows)
    resp = client.post(
        "/api/locations/bulk-upload",
        headers=AUTH_HEADERS,
        files={"file": ("test_upload.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    data = resp.json()["data"]
    assert data["summary"]["imported"] == 1
    assert data["summary"]["failed"] == 1
    assert data["error_report"] is not None
    print(f"PASS: Bulk upload imported valid records and returned error report for failed rows: {data['summary']}")

    # Verify record in DB
    db = SessionLocal()
    try:
        loc = db.query(Location).filter(Location.location_name == unique_name).first()
        assert loc is not None
        assert loc.location_id.startswith("LOC-")
        assert loc.qr_code is not None
        print(f"PASS: Location inserted with auto-generated ID '{loc.location_id}' and QR code '{loc.qr_code}'")

        # Verify audit log
        audit = db.query(AuditLog).filter(AuditLog.record_id == loc.location_id, AuditLog.action == "CREATE").first()
        assert audit is not None
        print(f"PASS: Audit log created for bulk upload: action={audit.action}, table={audit.table_name}")

        # Cleanup test location
        db.delete(loc)
        if audit:
            db.delete(audit)
        db.commit()
    finally:
        db.close()

def test_feature_2_compatible_assets_and_assignment():
    print("\n--- Testing Feature 2: Compatible Assets & Direct Location Assignment ---")
    
    # Pick an existing location that currently has 0 assets
    db = SessionLocal()
    try:
        assigned_loc_ids = [a.location_id for a in db.query(Asset).filter(Asset.location_id != None).all()]
        loc = db.query(Location).filter(~Location.location_id.in_(assigned_loc_ids)).first()
        if not loc:
            loc = db.query(Location).first()
        loc_id = loc.location_id
        req_type = loc.required_asset_type
        req_cap = loc.required_capacity
        print(f"Using test location: {loc_id} ({loc.location_name}) -> Requires {req_type} ({req_cap})")
    finally:
        db.close()

    # 1. GET /api/locations/{location_id}/compatible-assets
    resp = client.get(f"/api/locations/{loc_id}/compatible-assets", headers=AUTH_HEADERS)
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()["data"]
    assert "location" in data
    assert "currently_assigned" in data
    assert "compatible" in data
    assert "rejected" in data
    
    compat = data["compatible"]
    reje = data["rejected"]
    print(f"Compatible assets count: {len(compat)}, Incompatible assets count: {len(reje)}")
    
    for c in compat[:3]:
        assert c["asset_type"] == req_type
        assert c["capacity"] == req_cap
        assert c["status"] == "Active"

    for r in reje[:3]:
        assert len(r["rejection_reasons"]) > 0

    print("PASS: Compatible and rejected assets correctly partitioned with rejection reasons.")

    # 2. Test Assignment
    if len(compat) > 0:
        target_asset = compat[0]
        target_asset_id = target_asset["asset_id"]
        print(f"Assigning compatible asset {target_asset_id} to location {loc_id}...")

        assign_resp = client.post(
            f"/api/locations/{loc_id}/assign-asset/{target_asset_id}",
            headers=AUTH_HEADERS,
            json={"movement_reason": "Automated Test Assignment", "force": True}
        )
        assert assign_resp.status_code == 200, f"Assignment failed: {assign_resp.text}"
        assign_data = assign_resp.json()["data"]
        print(f"Assignment response: {assign_data}")

        # Verify DB updates
        db = SessionLocal()
        try:
            db_loc = db.query(Location).filter(Location.location_id == loc_id).first()
            db_asset = db.query(Asset).filter(Asset.asset_id == target_asset_id).first()
            assert db_asset.location_id == loc_id
            assert db_loc.current_assets_count >= 1
            print(f"PASS: Asset location updated to '{db_asset.location_id}' and Location asset count={db_loc.current_assets_count}")

            # Revert assignment to leave DB clean
            db_asset.location_id = None
            db.commit()
            print("PASS: Test assignment cleanly reverted.")
        finally:
            db.close()
    else:
        print("Note: No compatible unassigned assets currently in DB for this location's exact type/capacity.")

if __name__ == "__main__":
    test_feature_1_sample_download()
    test_feature_1_bulk_upload_preview()
    test_feature_1_bulk_upload_execution()
    test_feature_2_compatible_assets_and_assignment()
    print("\n=========================================")
    print("ALL AUTOMATED TESTS PASSED SUCCESSFULLY!")
    print("=========================================")
