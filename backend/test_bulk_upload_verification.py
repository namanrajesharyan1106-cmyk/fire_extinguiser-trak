import io
import sys
import openpyxl
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app import models
from app.core.security import create_access_token

def setup_master_data(db):
    print("Setting up master data...")
    # Plant
    if not db.query(models.Plant).filter(models.Plant.plant_name == "PP02").first():
        db.add(models.Plant(plant_code="P02", plant_name="PP02", status="Active"))
    # Department
    if not db.query(models.Department).filter(models.Department.dept_name == "Production").first():
        db.add(models.Department(dept_code="PROD", dept_name="Production", status="Active"))
    # Area
    if not db.query(models.MasterArea).filter(models.MasterArea.name == "Assembly").first():
        db.add(models.MasterArea(name="Assembly", is_active=True))
    # Building
    if not db.query(models.MasterBuilding).filter(models.MasterBuilding.name == "Main Building").first():
        db.add(models.MasterBuilding(name="Main Building", is_active=True))
    # Floor
    if not db.query(models.MasterFloor).filter(models.MasterFloor.name == "Ground").first():
        db.add(models.MasterFloor(name="Ground", is_active=True))
    # Asset
    if not db.query(models.MasterAssetType).filter(models.MasterAssetType.name == "ABC").first():
        db.add(models.MasterAssetType(name="ABC", is_active=True))
    # Capacity
    if not db.query(models.MasterCapacityType).filter(models.MasterCapacityType.name == "8kg").first():
        db.add(models.MasterCapacityType(name="8kg", is_active=True))
    db.commit()

def run_test():
    db = SessionLocal()
    
    setup_master_data(db)
    
    admin_user = db.query(models.User).filter(models.User.role == "ADMIN").first()
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    db.close()
    
    # Create excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "Location ID", "Location Name", "Plant", "Area", "Department", 
        "Building", "Floor", "Required Asset", "Capacity", "QR Code Value (Optional)"
    ])
    ws.append([
        "LOC_TEST_102", "Test Assembly 2", " PP02 ", "assembly", "PRODUCTION", 
        "Main Building", " ground ", "ABC", "8kg", ""
    ])
    
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    client = TestClient(app)
    response = client.post(
        "/api/locations/bulk-upload", 
        headers=headers,
        files={"file": ("test.xlsx", stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    
    print("Status Code:", response.status_code)
    try:
        data = response.json()
        print("Response Summary:", data.get("data", {}).get("summary"))
        summary = data.get("data", {}).get("summary", {})
        if data.get("success") and summary.get("imported") == 1:
            print("Test passed! Bulk upload successful.")
            sys.exit(0)
        else:
            print("Test failed! Row was not imported.")
            error_report = data.get("data", {}).get("error_report")
            if error_report:
                import base64
                decoded = base64.b64decode(error_report)
                err_wb = openpyxl.load_workbook(io.BytesIO(decoded))
                err_ws = err_wb.active
                for row in err_ws.iter_rows(values_only=True):
                    print(row)
            sys.exit(1)
    except Exception as e:
        print("Exception:", e)
        sys.exit(1)

if __name__ == "__main__":
    run_test()
