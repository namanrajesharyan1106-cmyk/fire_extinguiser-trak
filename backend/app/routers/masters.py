"""
Master Data Management Router
"""

import io
from typing import List, Dict, Any
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .. import models
from ..core import database
from ..core import dependencies as auth
from ..schemas.base import APIResponse

router = APIRouter()

# Schema for new Masters
class MasterCreateUpdate(BaseModel):
    name: str

class MasterResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    
class GenericMasterResponse(BaseModel):
    id: int
    name: str
    status: str

# Helper to map master type to model class
MASTER_MODELS = {
    "plants": models.MasterPlant,
    "departments": models.MasterDepartment,
    "areas": models.MasterArea,
    "buildings": models.MasterBuilding,
    "floors": models.MasterFloor,
    "asset_types": models.MasterAssetType,
    "capacity_types": models.MasterCapacityType,
    "risk_categories": models.MasterRiskCategory,
    "inspection_frequencies": models.MasterInspectionFrequency,
}

@router.get("/active")
def get_active_masters(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Fetch all active master data for dropdowns."""
    data = {}
    # Fetch active records for all master models
    for key, model_cls in MASTER_MODELS.items():
        records = db.query(model_cls).filter(model_cls.is_active == True).order_by(model_cls.name).all()
        data[key] = [{"id": r.id, "name": r.name} for r in records]
        
    return {"success": True, "message": "Master data retrieved", "data": data, "errors": None}


# Admin CRUD Endpoints
@router.get("/admin/{master_type}")
def get_admin_masters(master_type: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_roles(["ADMIN"]))):
        
    model_cls = MASTER_MODELS.get(master_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Master type not found")
        
    records = db.query(model_cls).order_by(model_cls.name).all()
    return {"success": True, "data": [{"id": r.id, "name": r.name, "is_active": r.is_active} for r in records]}


@router.post("/admin/{master_type}")
def create_master(master_type: str, payload: MasterCreateUpdate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_roles(["ADMIN"]))):
        
    model_cls = MASTER_MODELS.get(master_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Master type not found")
        
    existing = db.query(model_cls).filter(model_cls.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Name already exists")
        
    new_record = model_cls(name=payload.name, is_active=True)
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return {"success": True, "data": {"id": new_record.id, "name": new_record.name, "is_active": new_record.is_active}}


@router.put("/admin/{master_type}/{id}")
def update_master(master_type: str, id: int, payload: MasterCreateUpdate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_roles(["ADMIN"]))):
        
    model_cls = MASTER_MODELS.get(master_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Master type not found")
        
    record = db.query(model_cls).filter(model_cls.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    existing = db.query(model_cls).filter(model_cls.name == payload.name, model_cls.id != id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Name already exists")
        
    record.name = payload.name
    db.commit()
    db.refresh(record)
    return {"success": True, "data": {"id": record.id, "name": record.name, "is_active": record.is_active}}


@router.put("/admin/{master_type}/{id}/toggle-status")
def toggle_master_status(master_type: str, id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.require_roles(["ADMIN"]))):
        
    model_cls = MASTER_MODELS.get(master_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Master type not found")
        
    record = db.query(model_cls).filter(model_cls.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    record.is_active = not record.is_active
    db.commit()
    return {"success": True, "data": {"id": record.id, "is_active": record.is_active}}


@router.get("/admin/{master_type}/bulk-upload/sample")
def download_sample_excel(master_type: str, current_user: models.User = Depends(auth.require_roles(["ADMIN"]))):
    """Generate and return a sample Excel file for the given master type."""
    model_cls = MASTER_MODELS.get(master_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Master type not found")
        
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sample"
    
    # Add instructions sheet
    ws_instr = wb.create_sheet(title="Instructions")
    ws_instr.append([f"Instructions for {master_type.replace('_', ' ').title()} Bulk Upload"])
    ws_instr.append(["1. Fill out the Sample sheet."])
    ws_instr.append(["2. Do not modify the column headers."])
    ws_instr.append(["3. The 'Name' field is mandatory and must be unique."])
    ws_instr.append(["4. The 'Status' field is optional (defaults to Active). Use 'Active' or 'Inactive'."])
    ws_instr.append(["5. If any row fails validation, no records will be inserted and an Error Report will be generated."])
    
    # Define headers
    headers = ["Name", "Status"]
    ws.append(headers)
    
    # Add example row
    ws.append(["Example Name", "Active"])
    
    # Add data validation for Status column (B)
    dv = DataValidation(type="list", formula1='"Active,Inactive"', allow_blank=True)
    dv.error = "Status must be either Active or Inactive"
    dv.errorTitle = "Invalid Status"
    dv.prompt = "Please select Active or Inactive"
    dv.promptTitle = "Status Selection"
    ws.add_data_validation(dv)
    # Apply to all rows in column B (from row 2 to 1048576)
    dv.add(f"B2:B1048576")
    
    # Make headers bold
    from openpyxl.styles import Font
    for cell in ws[1]:
        cell.font = Font(bold=True)
        
    # Auto-adjust column widths
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 15
    
    # Save to memory
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    # Return as StreamingResponse
    headers_dict = {
        'Content-Disposition': f'attachment; filename="{master_type}_sample.xlsx"'
    }
    return StreamingResponse(
        stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers_dict
    )


@router.post("/admin/{master_type}/bulk-upload")
def bulk_upload_masters(
    master_type: str, 
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(auth.require_roles(["ADMIN"]))
):
    """Process uploaded Excel file and create master records."""
    import base64
    from openpyxl.styles import Font, PatternFill
    
    model_cls = MASTER_MODELS.get(master_type)
    if not model_cls:
        raise HTTPException(status_code=404, detail="Master type not found")
        
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an .xlsx file")
        
    try:
        contents = file.file.read()
        wb = openpyxl.load_workbook(filename=io.BytesIO(contents), data_only=True)
        if "Sample" in wb.sheetnames:
            ws = wb["Sample"]
        else:
            ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to read the Excel file")
        
    rows = list(ws.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        raise HTTPException(status_code=400, detail="File is empty or contains no data rows")
        
    # Check headers (basic validation)
    headers = [str(h).strip().lower() for h in rows[0] if h is not None]
    if not headers or headers[0] != "name":
        raise HTTPException(status_code=400, detail="Invalid columns. First column must be 'Name'")
        
    records_to_insert = []
    skipped = 0
    added = 0
    
    # To check duplicates within the file itself
    seen_names_in_file = set()
    
    # Extract existing names from DB for fast duplicate checking
    existing_records = db.query(model_cls.name).all()
    existing_names_in_db = {r[0].lower() for r in existing_records if r[0]}
    
    failed_rows = []
    expected_headers = [str(h) if h else "" for h in rows[0]]
    
    for idx, row in enumerate(rows[1:], start=2): # start=2 because rows is 0-indexed but excel rows are 1-indexed, and we skip header
        if not any(row):
            skipped += 1
            continue
            
        name_val = row[0] if len(row) > 0 else None
        status_val = row[1] if len(row) > 1 else None
        
        errors = []
        if name_val is None or str(name_val).strip() == "":
            errors.append("Name is required")
        else:
            name = str(name_val).strip()
            # Check if already processed in this file
            if name.lower() in seen_names_in_file:
                errors.append(f"Duplicate Name '{name}' within the Excel file")
                
            # Check if exists in DB
            if name.lower() in existing_names_in_db:
                errors.append(f"'{name}' already exists")
                
        if errors:
            failed_row = list(row) + ["; ".join(errors)]
            failed_rows.append(failed_row)
            continue
            
        is_active = True
        if status_val is not None:
            s_val = str(status_val).strip().lower()
            if s_val == "inactive":
                is_active = False
                
        # Valid record
        seen_names_in_file.add(name.lower())
        records_to_insert.append(model_cls(name=name, is_active=is_active))
        added += 1
        
    error_report_base64 = None
    if failed_rows:
        # All or nothing: if there are any failures, abort insertion
        added = 0
        error_wb = openpyxl.Workbook()
        error_ws = error_wb.active
        error_ws.title = "Failed Rows"
        
        error_ws.append(expected_headers + ["Error Details"])
        
        header_fill = PatternFill(start_color="D9EDF7", end_color="D9EDF7", fill_type="solid")
        header_font = Font(bold=True)
        for col_num, cell in enumerate(error_ws[1], 1):
            cell.fill = header_fill
            cell.font = header_font
            
        for f_row in failed_rows:
            error_ws.append(f_row)
            
        stream = io.BytesIO()
        error_wb.save(stream)
        error_report_base64 = base64.b64encode(stream.getvalue()).decode('utf-8')
        
        return {
            "success": False,
            "added": 0,
            "skipped": skipped,
            "errors": len(failed_rows),
            "message": f"Bulk upload failed. Found {len(failed_rows)} errors.",
            "error_report": error_report_base64
        }
        
    if records_to_insert:
        try:
            db.bulk_save_objects(records_to_insert)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to save records to database")
            
    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "errors": 0,
        "message": f"Bulk upload completed successfully. Added: {added}"
    }
