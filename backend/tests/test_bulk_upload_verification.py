import io
import openpyxl
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app import models
from app.core.security import create_access_token

def setup_master_data(db):
    if not db.query(models.MasterPlant).filter(models.MasterPlant.name == "PP02").first():
        db.add(models.MasterPlant(name="PP02", is_active=True))
    if not db.query(models.MasterDepartment).filter(models.MasterDepartment.name == "Production").first():
        db.add(models.MasterDepartment(name="Production", is_active=True))
    if not db.query(models.MasterArea).filter(models.MasterArea.name == "Assembly").first():
        db.add(models.MasterArea(name="Assembly", is_active=True))
    if not db.query(models.MasterBuilding).filter(models.MasterBuilding.name == "Main Building").first():
        db.add(models.MasterBuilding(name="Main Building", is_active=True))
    if not db.query(models.MasterFloor).filter(models.MasterFloor.name == "Ground").first():
        db.add(models.MasterFloor(name="Ground", is_active=True))
    if not db.query(models.MasterAssetType).filter(models.MasterAssetType.name == "ABC").first():
        db.add(models.MasterAssetType(name="ABC", is_active=True))
    if not db.query(models.MasterCapacityType).filter(models.MasterCapacityType.name == "8kg").first():
        db.add(models.MasterCapacityType(name="8kg", is_active=True))
    db.commit()

def test_bulk_upload_location():
    db = SessionLocal()
    try:
        setup_master_data(db)
        admin_user = db.query(models.User).filter(models.User.role == "ADMIN").first()
        token = create_access_token(data={"sub": str(admin_user.id)})
    finally:
        db.close()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create excel with official headers
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "Location Name", "Plant", "Area", "Department", 
        "Building", "Floor", "Required Asset Type", "Required Capacity", "QR Code Value (Optional)"
    ])
    ws.append([
        "Test Assembly 2 Unique", "PP02", "Assembly", "Production", 
        "Main Building", "Ground", "ABC", "8kg", ""
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
    
    assert response.status_code == 200, f"Bulk upload failed: {response.text}"
    data = response.json()
    assert data.get("success") is True
