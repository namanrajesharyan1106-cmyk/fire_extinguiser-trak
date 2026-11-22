import io
import sys
import os
import openpyxl

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Asset, User, AuditLog, MasterAssetType, MasterCapacityType, Location
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
            "Serial Number", "Asset Type", "Capacity", "Manufacturer", "Model",
            "Manufacturing Date", "Installation Date", "Expiry Date", "Status", "Location", "Remarks"
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

def test_1_sample_download():
    print("\n--- Testing 1: Asset Sample Template Download ---")
    resp = client.get("/api/assets/bulk-upload/sample", headers=AUTH_HEADERS)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert "openxmlformats" in resp.headers["content-type"]
    
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    ws = wb.active
    headers = [cell.value for cell in ws[1] if cell.value is not None]
    print(f"Sample Headers: {headers}")
    assert "Serial Number" in headers
    assert "Asset Type" in headers
    assert "Capacity" in headers
    assert "Manufacturer" in headers
    assert "Manufacturing Date" in headers
    assert "Installation Date" in headers
    assert "Expiry Date" in headers
    assert "Status" in headers
    assert "Location" in headers
    print("PASS: Asset sample template generated with correct headers and master data dropdowns.")

def test_2_preview_validation():
    print("\n--- Testing 2: Asset Bulk Upload Preview & Validation ---")
    
    # 1. Valid Row
    valid_rows = [
        ["SN-AUTOTEST-001", "ABC", "6kg", "Ceasefire", "Pro-Model", "2024-01-10", "2024-01-15", "2029-01-10", "Active", "", "Test Valid Asset"]
    ]
    file_bytes = create_excel_file(valid_rows)
    resp = client.post(
        "/api/assets/bulk-upload/preview",
        headers=AUTH_HEADERS,
        files={"file": ("test_preview.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert resp.status_code == 200, f"Preview failed: {resp.text}"
    data = resp.json()["data"]
    assert data["summary"]["total"] == 1
    assert data["summary"]["valid"] == 1
    assert data["summary"]["invalid"] == 0
    assert data["preview"][0]["status_code"] == "VALID"
    print("PASS: Valid asset row preview verified.")

    # 2. Invalid Asset Type & Capacity
    invalid_rows = [
        ["SN-AUTOTEST-INVALID", "NON_EXISTENT_TYPE", "999kg", "TestMake", "", "2024-01-10", "2024-01-15", "2029-01-10", "Active", "", ""]
    ]
    file_bytes2 = create_excel_file(invalid_rows)
    resp2 = client.post(
        "/api/assets/bulk-upload/preview",
        headers=AUTH_HEADERS,
        files={"file": ("test_invalid.xlsx", file_bytes2, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert resp2.status_code == 200
    data2 = resp2.json()["data"]
    assert data2["summary"]["invalid"] == 1
    assert data2["preview"][0]["status_code"] == "INVALID"
    err_msgs = " ".join(data2["preview"][0]["errors"])
    assert "Invalid Asset Type" in err_msgs
    assert "Invalid Capacity" in err_msgs
    print(f"PASS: Invalid Asset Type and Capacity correctly caught: {data2['preview'][0]['errors']}")

    # 3. Duplicate Serial Number (Intra-file duplicate)
    dup_rows = [
        ["SN-AUTOTEST-DUP", "ABC", "6kg", "Brand A", "", "2024-01-10", "", "2029-01-10", "Active", "", ""],
        ["SN-AUTOTEST-DUP", "ABC", "6kg", "Brand B", "", "2024-01-10", "", "2029-01-10", "Active", "", ""]
    ]
    file_bytes3 = create_excel_file(dup_rows)
    resp3 = client.post(
        "/api/assets/bulk-upload/preview",
        headers=AUTH_HEADERS,
        files={"file": ("test_dups.xlsx", file_bytes3, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert resp3.status_code == 200
    data3 = resp3.json()["data"]
    assert data3["summary"]["duplicates"] == 1
    assert data3["summary"]["valid"] == 1
    assert data3["preview"][1]["status_code"] == "DUPLICATE"
    print("PASS: Intra-file duplicate Serial Number correctly detected.")

    # 4. Invalid Location Detection
    invalid_loc_rows = [
        ["SN-AUTOTEST-BADLOC", "ABC", "6kg", "Ceasefire", "", "", "", "", "Active", "NON_EXISTENT_LOCATION_ID_999", ""]
    ]
    file_bytes4 = create_excel_file(invalid_loc_rows)
    resp4 = client.post(
        "/api/assets/bulk-upload/preview",
        headers=AUTH_HEADERS,
        files={"file": ("test_badloc.xlsx", file_bytes4, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert resp4.status_code == 200
    data4 = resp4.json()["data"]
    assert data4["summary"]["invalid"] == 1
    assert any("Location 'NON_EXISTENT_LOCATION_ID_999' not found" in err for err in data4["preview"][0]["errors"])
    print("PASS: Non-existent location correctly rejected.")

def test_3_bulk_upload_execution_and_rollback():
    print("\n--- Testing 3: Asset Bulk Upload Execution & Data Safety ---")
    
    unique_sn1 = "SN-EXEC-TEST-001"
    unique_sn2 = "SN-EXEC-TEST-002"
    invalid_sn = "SN-EXEC-INVALID"
    
    rows = [
        [unique_sn1, "ABC", "6kg", "Ceasefire", "Model-A", "2024-01-01", "2024-01-05", "2029-01-01", "Active", "", "Batch import 1"],
        [unique_sn2, "CO2", "4.5kg", "Amerex", "Model-B", "2024-02-01", "2024-02-05", "2029-02-01", "Active", "", "Batch import 2"],
        [invalid_sn, "INVALID_ASSET_TYPE", "99kg", "", "", "", "", "", "Active", "", "Should fail"]
    ]
    
    file_bytes = create_excel_file(rows)
    resp = client.post(
        "/api/assets/bulk-upload",
        headers=AUTH_HEADERS,
        files={"file": ("test_exec.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    data = resp.json()["data"]
    summary = data["summary"]
    print(f"Import Summary: {summary}")
    assert summary["total"] == 3
    assert summary["imported"] == 2
    assert summary["failed"] == 1
    assert data["error_report"] is not None
    print("PASS: 2 valid assets imported, 1 invalid asset safely failed, error report generated.")

    # Verify records in Database
    db = SessionLocal()
    try:
        a1 = db.query(Asset).filter(Asset.serial_number == unique_sn1).first()
        a2 = db.query(Asset).filter(Asset.serial_number == unique_sn2).first()
        assert a1 is not None, f"Asset {unique_sn1} not found in DB"
        assert a2 is not None, f"Asset {unique_sn2} not found in DB"
        
        # Verify auto-generated Asset ID format
        assert a1.asset_id.startswith("AST-")
        assert a2.asset_id.startswith("AST-")
        print(f"PASS: Auto-generated Asset IDs verified: {a1.asset_id}, {a2.asset_id}")
        
        # Verify barcode
        assert a1.barcode == a1.asset_id
        
        # Verify Audit Logs
        audit1 = db.query(AuditLog).filter(AuditLog.record_id == a1.asset_id, AuditLog.action == "CREATE").first()
        assert audit1 is not None
        print(f"PASS: Audit log verified for {a1.asset_id}: action={audit1.action}, table={audit1.table_name}")

        # Test duplicate prevention on second upload of the same serials
        dup_file_bytes = create_excel_file([
            [unique_sn1, "ABC", "6kg", "Ceasefire", "", "", "", "", "Active", "", "Duplicate upload"]
        ])
        dup_resp = client.post(
            "/api/assets/bulk-upload",
            headers=AUTH_HEADERS,
            files={"file": ("test_dup_exec.xlsx", dup_file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        assert dup_resp.status_code == 200
        dup_summary = dup_resp.json()["data"]["summary"]
        assert dup_summary["duplicates"] == 1
        assert dup_summary["imported"] == 0
        print(f"PASS: Re-uploading existing serial number correctly flagged as duplicate: {dup_summary}")

        # Cleanup test records
        db.query(AuditLog).filter(AuditLog.record_id.in_([a1.asset_id, a2.asset_id])).delete()
        db.delete(a1)
        db.delete(a2)
        db.commit()
        print("PASS: Test assets and audit logs cleanly reverted.")
    finally:
        db.close()

if __name__ == "__main__":
    test_1_sample_download()
    test_2_preview_validation()
    test_3_bulk_upload_execution_and_rollback()
    print("\n==========================================")
    print("ALL ASSET BULK UPLOAD TESTS PASSED SUCCESSFULLY!")
    print("==========================================")
