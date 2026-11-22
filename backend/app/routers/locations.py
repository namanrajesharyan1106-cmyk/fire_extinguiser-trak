"""
Locations router — CRUD + QR generation + scan endpoint.
"""

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import exc, or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.config import settings
from ..core import database
from ..core import dependencies as auth
from ..schemas.base import APIResponse
from ..utils import create_audit_log, generate_qr_code_image
from ..core.scope import apply_scope, check_record_scope, get_user_scope
import io
import base64
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import openpyxl
from openpyxl.styles import Font, PatternFill

router = APIRouter()


def create_api_response(success: bool, message: str, data=None, errors=None) -> dict:
    return {"success": success, "message": message, "data": data, "errors": errors}

def generate_system_id(db: Session, entity_type: str, plant: str = None) -> str:
    from datetime import datetime
    configs = {c.key: c.value for c in db.query(models.SystemConfig).all()}
    default_prefix = "LOC" if entity_type == "location" else ("AST" if entity_type == "asset" else entity_type.upper()[:3])
    prefix = configs.get(f"{entity_type}_prefix", default_prefix)
    plant_wise = configs.get("plant_wise_numbering", "false").lower() == "true"
    reset_yearly = configs.get("reset_yearly", "false").lower() == "true"
    
    current_year = datetime.now().year if reset_yearly else None
    tracker_plant = plant if plant_wise and plant else None
    
    tracker = db.query(models.SequenceTracker).filter(
        models.SequenceTracker.entity_type == entity_type,
        models.SequenceTracker.plant == tracker_plant,
        models.SequenceTracker.year == current_year
    ).with_for_update().first()
    
    if not tracker:
        tracker = models.SequenceTracker(
            entity_type=entity_type,
            plant=tracker_plant,
            year=current_year,
            last_value=0
        )
        db.add(tracker)
        db.flush()
        
    tracker.last_value += 1
    seq_num = f"{tracker.last_value:06d}"
    
    parts = []
    if plant_wise and tracker_plant:
        parts.append(tracker_plant)
    if prefix:
        parts.append(prefix)
    if reset_yearly:
        parts.append(str(current_year)[-2:])
    parts.append(seq_num)
    
    return "-".join(parts)


class MasterDataService:
    @staticmethod
    def get_active_masters(db: Session):
        return {
            "plants": [r.name.strip() for r in db.query(models.MasterPlant).filter(models.MasterPlant.is_active).order_by(models.MasterPlant.name).all() if r.name and r.name.strip()],
            "areas": [r.name.strip() for r in db.query(models.MasterArea).filter(models.MasterArea.is_active).order_by(models.MasterArea.name).all() if r.name and r.name.strip()],
            "depts": [r.name.strip() for r in db.query(models.MasterDepartment).filter(models.MasterDepartment.is_active).order_by(models.MasterDepartment.name).all() if r.name and r.name.strip()],
            "buildings": [r.name.strip() for r in db.query(models.MasterBuilding).filter(models.MasterBuilding.is_active).order_by(models.MasterBuilding.name).all() if r.name and r.name.strip()],
            "floors": [r.name.strip() for r in db.query(models.MasterFloor).filter(models.MasterFloor.is_active).order_by(models.MasterFloor.name).all() if r.name and r.name.strip()],
            "assets": [r.name.strip() for r in db.query(models.MasterAssetType).filter(models.MasterAssetType.is_active).order_by(models.MasterAssetType.name).all() if r.name and r.name.strip()],
            "caps": [r.name.strip() for r in db.query(models.MasterCapacityType).filter(models.MasterCapacityType.is_active).order_by(models.MasterCapacityType.name).all() if r.name and r.name.strip()]
        }

class LocationMasterValidator:
    def __init__(self, db: Session):
        masters = MasterDataService.get_active_masters(db)
        self.plants = {p.strip().lower() for p in masters["plants"] if p}
        self.areas = {a.strip().lower() for a in masters["areas"] if a}
        self.depts = {d.strip().lower() for d in masters["depts"] if d}
        self.buildings = {b.strip().lower() for b in masters["buildings"] if b}
        self.floors = {f.strip().lower() for f in masters["floors"] if f}
        
        self.asset_map = {r.name.strip().lower(): r.id for r in db.query(models.MasterAssetType).filter(models.MasterAssetType.is_active).all() if r.name and r.name.strip()}
        self.cap_map = {r.name.strip().lower(): r.id for r in db.query(models.MasterCapacityType).filter(models.MasterCapacityType.is_active).all() if r.name and r.name.strip()}
        
    def validate_strings(self, plant: Optional[str], area: Optional[str], department: Optional[str], building: Optional[str], floor: Optional[str]) -> list[str]:
        errors = []
        if plant and plant.strip().lower() not in self.plants:
            errors.append(f"Invalid Plant '{plant}'")
        if area and area.strip().lower() not in self.areas:
            errors.append(f"Invalid Area '{area}'")
        if department and department.strip().lower() not in self.depts:
            errors.append(f"Invalid Department '{department}'")
        if building and building.strip().lower() not in self.buildings:
            errors.append(f"Invalid Building '{building}'")
        if floor and floor.strip().lower() not in self.floors:
            errors.append(f"Invalid Floor '{floor}'")
        return errors
        
    def resolve_asset_capacity(self, req_asset: Optional[str], capacity: Optional[str]):
        errors = []
        asset_id = self.asset_map.get(req_asset.strip().lower()) if req_asset else None
        cap_id = self.cap_map.get(capacity.strip().lower()) if capacity else None
        
        if req_asset and not asset_id:
            errors.append(f"Invalid Asset Type '{req_asset}'")
        if capacity and not cap_id:
            errors.append(f"Invalid Capacity '{capacity}'")
        
        return asset_id, cap_id, errors


def check_and_map_headers(row_headers):
    expected_standard = [
        "Location Name", "Plant", "Area", "Department", 
        "Building", "Floor", "Required Asset Type", "Required Capacity", "QR Code Value (Optional)"
    ]
    def norm(h):
        if not h:
            return ""
        h_str = str(h).strip().lower()
        if h_str in ["required asset", "required asset type", "asset type", "asset"]:
            return "required asset type"
        if h_str in ["capacity", "required capacity"]:
            return "required capacity"
        if h_str in ["qr code value (optional)", "qr code value", "qr code", "qr"]:
            return "qr code value (optional)"
        return h_str

    actual_norm = [norm(h) for h in row_headers[:9]]
    expected_norm = [norm(h) for h in expected_standard]
    if actual_norm != expected_norm:
        return False, expected_standard
    return True, expected_standard


@router.get("", response_model=APIResponse[schemas.PaginatedLocationResponse])
def get_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    plant: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    risk_category: Optional[str] = None,
    sort_by: Optional[str] = Query(
        "newest", pattern="^(newest|oldest|alphabetical|last_updated)$"
    ),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_locations")),
):
    query = apply_scope(db.query(models.Location), current_user, db, models.Location)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.Location.location_name.ilike(search_term),
                models.Location.location_code.ilike(search_term),
                models.Location.plant.ilike(search_term),
                models.Location.department.ilike(search_term),
                models.Location.building.ilike(search_term),
                models.Location.floor.ilike(search_term),
                models.Location.area.ilike(search_term),
            )
        )

    if plant:
        query = query.filter(models.Location.plant == plant)
    if department:
        query = query.filter(models.Location.department == department)
    if status:
        query = query.filter(models.Location.status == status)
    if risk_category:
        query = query.filter(models.Location.risk_category == risk_category)

    if sort_by == "newest":
        query = query.order_by(models.Location.created_at.desc())
    elif sort_by == "oldest":
        query = query.order_by(models.Location.created_at.asc())
    elif sort_by == "alphabetical":
        query = query.order_by(models.Location.location_name.asc())
    elif sort_by == "last_updated":
        query = query.order_by(models.Location.updated_at.desc())

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return create_api_response(
        True, "Locations retrieved successfully", {"items": items, "total": total}
    )


@router.get("/bulk-upload/sample")
def download_bulk_upload_sample(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_location"))
):
    """Generate and return a sample Excel file for bulk location upload."""
    from openpyxl.worksheet.datavalidation import DataValidation
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Locations"
    
    ws_instr = wb.create_sheet(title="Instructions")
    ws_instr.append(["Instructions for Location Bulk Upload"])
    ws_instr.append(["1. Fill out the Locations sheet using the dropdowns provided."])
    ws_instr.append(["2. Do not modify the column headers."])
    ws_instr.append(["3. All fields except 'QR Code Value (Optional)' are mandatory."])
    ws_instr.append(["4. Location IDs are automatically generated by the system numbering service."])
    ws_instr.append(["5. Duplicate Location Name + Plant combinations will be rejected."])
    ws_instr.append(["6. If a row fails validation, an Error Report will be generated for you to download."])
    
    ws_master = wb.create_sheet(title="Master Data")
    ws_master.sheet_state = 'hidden'
    
    masters = MasterDataService.get_active_masters(db)
    plants = masters["plants"]
    areas = masters["areas"]
    depts = masters["depts"]
    buildings = masters["buildings"]
    floors = masters["floors"]
    assets = masters["assets"]
    caps = masters["caps"]
    
    max_len = max(len(plants), len(areas), len(depts), len(buildings), len(floors), len(assets), len(caps), 1)
    
    headers_master = ["Plant", "Area", "Department", "Building", "Floor", "Required Asset Type", "Required Capacity"]
    ws_master.append(headers_master)
    
    for i in range(max_len):
        row = [
            plants[i] if i < len(plants) else "",
            areas[i] if i < len(areas) else "",
            depts[i] if i < len(depts) else "",
            buildings[i] if i < len(buildings) else "",
            floors[i] if i < len(floors) else "",
            assets[i] if i < len(assets) else "",
            caps[i] if i < len(caps) else ""
        ]
        ws_master.append(row)
    
    headers = [
        "Location Name",
        "Plant",
        "Area",
        "Department",
        "Building",
        "Floor",
        "Required Asset Type",
        "Required Capacity",
        "QR Code Value (Optional)"
    ]
    
    ws.append(headers)
    
    # Provide 2 realistic sample rows
    ws.append([
        "Production Bay 1", 
        plants[0] if plants else "PP02", 
        areas[0] if areas else "Assembly", 
        depts[0] if depts else "Production", 
        buildings[0] if buildings else "Main Building", 
        floors[0] if floors else "Ground", 
        assets[0] if assets else "ABC", 
        caps[0] if caps else "8kg", 
        ""
    ])
    ws.append([
        "Warehouse Storage East", 
        plants[0] if plants else "PP02", 
        areas[1] if len(areas) > 1 else (areas[0] if areas else "Stores"), 
        depts[1] if len(depts) > 1 else (depts[0] if depts else "Logistics"), 
        buildings[1] if len(buildings) > 1 else (buildings[0] if buildings else "Main Plant"), 
        floors[0] if floors else "Ground", 
        assets[1] if len(assets) > 1 else (assets[0] if assets else "CO2"), 
        caps[1] if len(caps) > 1 else (caps[0] if caps else "4.5kg"), 
        ""
    ])
    
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    for col_num, cell in enumerate(ws[1], 1):
        cell.fill = header_fill
        cell.font = header_font
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 22
        
    def add_validation(dv_formula, col_letter):
        dv = DataValidation(type="list", formula1=dv_formula, allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{col_letter}2:{col_letter}1000")
        
    validation_map = {
        "Plant": (plants, "A"),
        "Area": (areas, "B"),
        "Department": (depts, "C"),
        "Building": (buildings, "D"),
        "Floor": (floors, "E"),
        "Required Asset Type": (assets, "F"),
        "Required Capacity": (caps, "G")
    }
    
    from openpyxl.utils import get_column_letter
    
    for col_idx, header_name in enumerate(headers, start=1):
        if header_name in validation_map:
            master_list, master_col = validation_map[header_name]
            if master_list:
                col_letter = get_column_letter(col_idx)
                add_validation(f"'Master Data'!${master_col}$2:${master_col}${len(master_list)+1}", col_letter)

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Location_Bulk_Upload_Sample.xlsx"}
    )


@router.post("/bulk-upload/preview")
def preview_bulk_upload_locations(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_location"))
):
    """Parse and validate Excel rows without writing to DB, returning row-by-row preview with error reasons."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file (.xlsx, .xls)")
        
    try:
        contents = file.file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
        
    rows = list(ws.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        raise HTTPException(status_code=400, detail="The Excel file is empty or missing data rows.")
        
    is_valid_header, expected_headers = check_and_map_headers(rows[0])
    if not is_valid_header:
        raise HTTPException(
            status_code=400, 
            detail="Invalid Excel Template. Headers must match the official sample template.",
            headers={"X-Template-Error": "true"}
        )
        
    validator = LocationMasterValidator(db)
    existing_locations = db.query(models.Location.location_id, models.Location.location_name, models.Location.plant, models.Location.qr_code).all()
    existing_name_plants = {(loc.location_name.strip().lower(), loc.plant.strip().lower()) for loc in existing_locations if loc.location_name and loc.plant}
    existing_qrs = {loc.qr_code.strip() for loc in existing_locations if loc.qr_code}
    
    seen_file_name_plants = set()
    seen_file_qrs = set()
    
    preview_rows = []
    valid_count = 0
    invalid_count = 0
    duplicate_count = 0
    
    for row_idx, row in enumerate(rows[1:], start=2):
        if not any(row):
            continue
            
        (
            loc_name, plant, area, department, 
            building, floor, req_asset, capacity, qr_raw
        ) = list(row)[:9] + [None] * max(0, 9 - len(row))
        
        loc_name_str = str(loc_name).strip() if loc_name is not None and str(loc_name).strip() != "" else None
        plant_str = str(plant).strip() if plant is not None and str(plant).strip() != "" else None
        area_str = str(area).strip() if area is not None and str(area).strip() != "" else None
        department_str = str(department).strip() if department is not None and str(department).strip() != "" else None
        building_str = str(building).strip() if building is not None and str(building).strip() != "" else None
        floor_str = str(floor).strip() if floor is not None and str(floor).strip() != "" else None
        req_asset_str = str(req_asset).strip() if req_asset is not None and str(req_asset).strip() != "" else None
        capacity_str = str(capacity).strip() if capacity is not None and str(capacity).strip() != "" else None
        qr_code_str = str(qr_raw).strip() if qr_raw is not None and str(qr_raw).strip() != "" else None
        
        errors = []
        is_duplicate = False
        
        # Mandatory field validation
        if not loc_name_str:
            errors.append("Location Name is required")
        if not plant_str:
            errors.append("Plant is required")
        if not area_str:
            errors.append("Area is required")
        if not department_str:
            errors.append("Department is required")
        if not building_str:
            errors.append("Building is required")
        if not floor_str:
            errors.append("Floor is required")
        if not req_asset_str:
            errors.append("Required Asset Type is required")
        if not capacity_str:
            errors.append("Required Capacity is required")
        
        # Master Data validation
        val_errors = validator.validate_strings(plant_str, area_str, department_str, building_str, floor_str)
        errors.extend(val_errors)
        
        asset_id, cap_id, ac_errors = validator.resolve_asset_capacity(req_asset_str, capacity_str)
        errors.extend(ac_errors)
        
        # Duplicate detection (DB and intra-file)
        if loc_name_str and plant_str:
            np_key = (loc_name_str.lower(), plant_str.lower())
            if np_key in existing_name_plants:
                errors.append(f"Location Name '{loc_name_str}' already exists in Plant '{plant_str}'")
                is_duplicate = True
            elif np_key in seen_file_name_plants:
                errors.append(f"Duplicate Location '{loc_name_str}' in Plant '{plant_str}' repeated in file")
                is_duplicate = True
            else:
                seen_file_name_plants.add(np_key)
                
        if qr_code_str:
            if qr_code_str in existing_qrs:
                errors.append(f"QR Code '{qr_code_str}' already exists in system")
                is_duplicate = True
            elif qr_code_str in seen_file_qrs:
                errors.append(f"QR Code '{qr_code_str}' repeated in file")
                is_duplicate = True
            else:
                seen_file_qrs.add(qr_code_str)
                
        if is_duplicate:
            status = "DUPLICATE"
            duplicate_count += 1
        elif errors:
            status = "INVALID"
            invalid_count += 1
        else:
            status = "VALID"
            valid_count += 1
            
        preview_rows.append({
            "row_number": row_idx,
            "location_name": loc_name_str or "",
            "plant": plant_str or "",
            "area": area_str or "",
            "department": department_str or "",
            "building": building_str or "",
            "floor": floor_str or "",
            "required_asset_type": req_asset_str or "",
            "required_capacity": capacity_str or "",
            "qr_code": qr_code_str or "",
            "status": status,
            "errors": errors
        })
        
    summary_dict = {
        "total": len(preview_rows),
        "valid": valid_count,
        "invalid": invalid_count,
        "duplicates": duplicate_count
    }
    return create_api_response(True, "Preview generated successfully", {
        "summary": summary_dict,
        "preview": preview_rows,
        "total_rows": len(preview_rows),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "duplicate_count": duplicate_count,
        "rows": preview_rows
    })


@router.post("/bulk-upload")
def bulk_upload_locations(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_location"))
):
    import logging
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file (.xlsx, .xls)")
        
    try:
        contents = file.file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
        
    rows = list(ws.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        raise HTTPException(status_code=400, detail="The Excel file is empty or missing data rows.")
        
    is_valid_header, expected_headers = check_and_map_headers(rows[0])
    if not is_valid_header:
        raise HTTPException(
            status_code=400, 
            detail="Invalid Excel Template. Headers must match the official sample template.",
            headers={"X-Template-Error": "true"}
        )
        
    total_rows = len(rows) - 1
    imported = 0
    failed = 0
    duplicates = 0
    skipped = 0
    
    failed_rows = []
    
    existing_locations = db.query(models.Location.location_id, models.Location.location_name, models.Location.plant, models.Location.qr_code).all()
    existing_ids = {loc.location_id for loc in existing_locations}
    existing_name_plants = {(loc.location_name.strip().lower(), loc.plant.strip().lower()) for loc in existing_locations if loc.location_name and loc.plant}
    existing_qrs = {loc.qr_code.strip() for loc in existing_locations if loc.qr_code}
    
    seen_file_name_plants = set()
    seen_file_qrs = set()
    
    validator = LocationMasterValidator(db)
    
    for row_idx, row in enumerate(rows[1:], start=2):
        if not any(row):
            skipped += 1
            continue
            
        (
            loc_name, plant, area, department, 
            building, floor, req_asset, capacity, qr_raw
        ) = list(row)[:9] + [None] * max(0, 9 - len(row))
        
        loc_name = str(loc_name).strip() if loc_name is not None and str(loc_name).strip() != "" else None
        plant = str(plant).strip() if plant is not None and str(plant).strip() != "" else None
        area = str(area).strip() if area is not None and str(area).strip() != "" else None
        department = str(department).strip() if department is not None and str(department).strip() != "" else None
        building = str(building).strip() if building is not None and str(building).strip() != "" else None
        floor = str(floor).strip() if floor is not None and str(floor).strip() != "" else None
        req_asset = str(req_asset).strip() if req_asset is not None and str(req_asset).strip() != "" else None
        capacity = str(capacity).strip() if capacity is not None and str(capacity).strip() != "" else None
        qr_code = str(qr_raw).strip() if qr_raw is not None and str(qr_raw).strip() != "" else None
        
        errors = []
        is_duplicate = False
        
        if not loc_name:
            errors.append("Location Name is required")
        if not plant:
            errors.append("Plant is required")
        if not area:
            errors.append("Area is required")
        if not department:
            errors.append("Department is required")
        if not building:
            errors.append("Building is required")
        if not floor:
            errors.append("Floor is required")
        if not req_asset:
            errors.append("Required Asset Type is required")
        if not capacity:
            errors.append("Required Capacity is required")
            
        validation_errors = validator.validate_strings(plant, area, department, building, floor)
        errors.extend(validation_errors)
        
        asset_id, cap_id, ac_errors = validator.resolve_asset_capacity(req_asset, capacity)
        errors.extend(ac_errors)

        if loc_name and plant:
            np_key = (loc_name.lower(), plant.lower())
            if np_key in existing_name_plants:
                errors.append(f"Location Name '{loc_name}' already exists in Plant '{plant}'")
                is_duplicate = True
            elif np_key in seen_file_name_plants:
                errors.append(f"Duplicate Location '{loc_name}' in Plant '{plant}' repeated in file")
                is_duplicate = True
            else:
                seen_file_name_plants.add(np_key)
            
        if qr_code:
            if qr_code in existing_qrs:
                errors.append(f"QR Code '{qr_code}' already exists")
                is_duplicate = True
            elif qr_code in seen_file_qrs:
                errors.append(f"QR Code '{qr_code}' repeated in file")
                is_duplicate = True
            else:
                seen_file_qrs.add(qr_code)

        if errors:
            if is_duplicate:
                duplicates += 1
            else:
                failed += 1
            failed_row = list(row)[:9] + ["; ".join(errors)]
            failed_rows.append(failed_row)
            continue
            
        from datetime import datetime
        loc_id = generate_system_id(db, "location", plant)
        
        new_location = models.Location(
            location_id=loc_id,
            location_name=loc_name,
            plant=plant,
            area=area,
            department=department,
            building=building,
            floor=floor,
            required_asset_type_id=asset_id,
            required_capacity_id=cap_id,
            qr_code=qr_code or loc_id,
            created_by_id=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            db.add(new_location)
            existing_ids.add(loc_id)
            existing_name_plants.add((loc_name.lower(), plant.lower()))
            existing_qrs.add(new_location.qr_code)
            
            db.commit()
            
            try:
                qr_path = generate_qr_code_image(new_location.qr_code, new_location.location_id)
                new_location.qr_image_path = qr_path
                db.commit()
            except Exception as e:
                logging.error(f"Failed to generate QR in bulk for {loc_id}: {e}")
                
            create_audit_log(db, current_user.id, "CREATE", "locations", loc_id)
            imported += 1
        except Exception as e:
            db.rollback()
            failed += 1
            failed_rows.append(list(row)[:9] + [f"Database error: {str(e)}"])
            
    db.commit()
    
    error_report_base64 = None
    if failed_rows:
        error_wb = openpyxl.Workbook()
        error_ws = error_wb.active
        error_ws.title = "Failed Rows"
        
        error_ws.append(expected_headers + ["Error Details"])
        
        header_fill = PatternFill(start_color="D9EDF7", end_color="D9EDF7", fill_type="solid")
        header_font = Font(bold=True)
        for col_num, cell in enumerate(error_ws[1], 1):
            cell.fill = header_fill
            cell.font = header_font
            error_ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 22
            
        for f_row in failed_rows:
            error_ws.append(f_row)
            
        stream = io.BytesIO()
        error_wb.save(stream)
        error_report_base64 = base64.b64encode(stream.getvalue()).decode('utf-8')

    return create_api_response(
        True, 
        "Bulk upload completed", 
        {
            "summary": {
                "total": total_rows,
                "imported": imported,
                "failed": failed,
                "duplicates": duplicates,
                "skipped": skipped
            },
            "error_report": error_report_base64
        }
    )


@router.get("/by-qr/{qr_value}", response_model=APIResponse[schemas.LocationResponse])
def get_location_by_qr(
    qr_value: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Scan QR → get location with current asset info."""
    location = (
        db.query(models.Location).filter(models.Location.qr_code == qr_value).first()
    )
    if not location or not check_record_scope(location, current_user, db):
        raise HTTPException(
            status_code=404, detail=f"No location found for QR code: '{qr_value}'"
        )
    return create_api_response(True, "Location retrieved", location)


@router.get("/{location_id}", response_model=APIResponse[schemas.LocationResponse])
def get_location(
    location_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_locations")),
):
    location = (
        db.query(models.Location)
        .filter(models.Location.location_id == location_id)
        .first()
    )
    if not location or not check_record_scope(location, current_user, db):
        raise HTTPException(status_code=404, detail="Location not found")
    return create_api_response(True, "Location retrieved", location)


@router.post("", response_model=APIResponse[schemas.LocationResponse], status_code=201)
def create_location(
    location: schemas.LocationCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_location")),
):
    import logging
    
    print("\n--- DEBUG Location Creation ---")
    print(f"Incoming Payload (raw): {location.model_dump()}")
    
    validator = LocationMasterValidator(db)
    validation_errors = validator.validate_strings(
        location.plant, location.area, location.department, 
        location.building, location.floor
    )
    if validation_errors:
        raise HTTPException(status_code=400, detail="; ".join(validation_errors))
        
    if location.required_asset_type_id not in validator.asset_map.values():
        raise HTTPException(status_code=400, detail="Invalid Required Asset Type ID")
    if location.required_capacity_id not in validator.cap_map.values():
        raise HTTPException(status_code=400, detail="Invalid Required Capacity ID")

    scope = get_user_scope(current_user, db)
    if not scope.is_global:
        if scope.is_empty or (location.plant and location.plant not in scope.plants):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Cannot create location for plant '{location.plant}' outside your assigned scope."
            )

    # Auto-generate location_id if not provided by client
    location_id = location.location_id or generate_system_id(db, "location", location.plant)

    print(f"Validated Schema: {location}")
    print(f"Generated Location ID: {location_id}")
    print(f"Resolved Asset Type ID: {location.required_asset_type_id}")
    print(f"Resolved Capacity ID: {location.required_capacity_id}")

    existing = (
        db.query(models.Location)
        .filter(models.Location.location_id == location_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Location ID already registered")

    if location.location_code:
        dup_code = (
            db.query(models.Location)
            .filter(models.Location.location_code == location.location_code)
            .first()
        )
        if dup_code:
            raise HTTPException(
                status_code=400,
                detail=f"Location code '{location.location_code}' already in use",
            )

    from datetime import datetime
    loc_data = location.model_dump(exclude={"location_id"})
    new_location = models.Location(
        **loc_data, 
        location_id=location_id, 
        created_by_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    if not new_location.qr_code:
        new_location.qr_code = location_id

    print(f"SQLAlchemy Model before insert: {new_location.__dict__}")

    try:
        db.add(new_location)
        db.commit()
        db.refresh(new_location)
    except exc.IntegrityError as e:
        db.rollback()
        logging.exception("Database integrity error during location creation")
        if "uq_location_name_plant" in str(e):
            raise HTTPException(
                status_code=400,
                detail=f"Location name '{location.location_name}' already exists in plant '{location.plant}'",
            )
        raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e.orig)}")

    # Generate QR image
    try:
        qr_path = generate_qr_code_image(new_location.qr_code, location_id)
        new_location.qr_image_path = qr_path
        db.commit()
    except Exception as e:
        import logging

        logging.error(
            f"Failed to generate QR code for location {location_id}: {e}"
        )

    create_audit_log(db, current_user.id, "CREATE", "locations", location_id)
    db.commit()
    return create_api_response(True, "Location created successfully", new_location)


@router.put("/{location_id}", response_model=APIResponse[schemas.LocationResponse])
def update_location(
    location_id: str,
    location: schemas.LocationUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("edit_location")),
):
    db_location = (
        db.query(models.Location)
        .filter(models.Location.location_id == location_id)
        .first()
    )
    if not db_location or not check_record_scope(db_location, current_user, db):
        raise HTTPException(status_code=404, detail="Location not found")
        
    validator = LocationMasterValidator(db)
    
    # We must validate the merged state
    new_plant = location.plant if location.plant is not None else db_location.plant
    new_area = location.area if location.area is not None else db_location.area
    new_dept = location.department if location.department is not None else db_location.department
    new_building = location.building if location.building is not None else db_location.building
    new_floor = location.floor if location.floor is not None else db_location.floor
    new_asset_id = location.required_asset_type_id if location.required_asset_type_id is not None else db_location.required_asset_type_id
    new_cap_id = location.required_capacity_id if location.required_capacity_id is not None else db_location.required_capacity_id
    
    validation_errors = validator.validate_strings(new_plant, new_area, new_dept, new_building, new_floor)
    if validation_errors:
        raise HTTPException(status_code=400, detail="; ".join(validation_errors))
        
    if new_asset_id not in validator.asset_map.values():
        raise HTTPException(status_code=400, detail="Invalid Required Asset Type ID")
    if new_cap_id not in validator.cap_map.values():
        raise HTTPException(status_code=400, detail="Invalid Required Capacity ID")

    for key, value in location.model_dump(exclude_unset=True).items():
        setattr(db_location, key, value)

    try:
        db.commit()
        db.refresh(db_location)
    except exc.IntegrityError as e:
        db.rollback()
        if "uq_location_name_plant" in str(e):
            raise HTTPException(
                status_code=400,
                detail="A location with this name already exists in the same plant",
            )
        raise HTTPException(status_code=400, detail="Database integrity error")

    create_audit_log(db, current_user.id, "UPDATE", "locations", location_id)
    db.commit()
    return create_api_response(True, "Location updated successfully", db_location)


@router.delete("/{location_id}", response_model=APIResponse[dict])
def delete_location(
    location_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("delete_location")),
):
    db_location = (
        db.query(models.Location)
        .filter(models.Location.location_id == location_id)
        .first()
    )
    if not db_location or not check_record_scope(db_location, current_user, db):
        raise HTTPException(status_code=404, detail="Location not found")

    # Safe Delete: Prevent deletion if an asset is currently assigned
    assigned_assets = db_location.assets or []
    if len(assigned_assets) > 0:
        first_asset_id = assigned_assets[0].asset_id
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete location '{location_id}' because asset '{first_asset_id}' is assigned. Unlink the asset first.",
        )

    db.delete(db_location)
    db.commit()

    create_audit_log(db, current_user.id, "DELETE", "locations", location_id)
    db.commit()
    return create_api_response(
        True, f"Location '{location_id}' deleted successfully", {}
    )


@router.post(
    "/{location_id}/generate-qr", response_model=APIResponse[schemas.LocationResponse]
)
def generate_qr_for_location(
    location_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("generate_qr")),
):
    """Generate or regenerate a QR code image for a location."""
    location = (
        db.query(models.Location)
        .filter(models.Location.location_id == location_id)
        .first()
    )
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    if not location.qr_code:
        location.qr_code = location_id

    qr_path = generate_qr_code_image(location.qr_code, location_id)
    location.qr_image_path = qr_path
    db.commit()
    db.refresh(location)
    return create_api_response(True, "QR Code generated successfully", location)


@router.get("/{location_id}/qr-image")
def get_qr_image(
    location_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Return QR code PNG image for a location (for printing)."""
    location = (
        db.query(models.Location)
        .filter(models.Location.location_id == location_id)
        .first()
    )
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    if not location.qr_image_path or os.path == False.exists(
        os.path.join(os.path.dirname(settings.UPLOAD_DIR), location.qr_image_path)
    ):
        qr_code_val = location.qr_code or location_id
        qr_path = generate_qr_code_image(qr_code_val, location_id)
        location.qr_image_path = qr_path
        db.commit()

    full_path = os.path.join(
        os.path.dirname(settings.UPLOAD_DIR), location.qr_image_path.lstrip("/")
    )
    if os.path == False.exists(full_path):
        raise HTTPException(status_code=404, detail="QR image not found")

    return FileResponse(full_path, media_type="image/png")


@router.get(
    "/{location_id}/inspection-history",
    response_model=APIResponse[List[schemas.InspectionResponse]],
)
def get_location_inspection_history(
    location_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_inspections")),
):
    location = (
        db.query(models.Location)
        .filter(models.Location.location_id == location_id)
        .first()
    )
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    inspections = (
        db.query(models.Inspection)
        .filter(models.Inspection.location_id == location_id)
        .order_by(models.Inspection.inspection_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return create_api_response(True, "Inspection history retrieved", inspections)


@router.get("/{location_id}/compatible-assets")
def get_compatible_assets_for_location(
    location_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_assets")),
):
    """
    Evaluate all assets for compatibility with a specific location.
    Categorizes into compatible, rejected (with reasons), and currently assigned.
    """
    from ..utils.asset_checks import is_asset_expired

    location = db.query(models.Location).filter(models.Location.location_id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail=f"Location '{location_id}' not found")

    # Currently assigned assets
    assigned_assets = (
        db.query(models.Asset)
        .filter(models.Asset.location_id == location_id)
        .all()
    )

    # Open maintenance tickets set
    open_maint_asset_ids = {
        m.asset_id for m in db.query(models.Maintenance.asset_id)
        .filter(models.Maintenance.status.notin_(["Closed", "Verified"]))
        .all()
    }

    all_assets = db.query(models.Asset).order_by(models.Asset.asset_id.asc()).all()

    compatible = []
    rejected = []

    for asset in all_assets:
        reasons = []
        is_compatible = True

        # 1. Asset Status
        if asset.status != "Active":
            reasons.append({
                "reason": "Asset Inactive",
                "expected": "Active",
                "actual": asset.status or "Inactive"
            })
            is_compatible = False

        # 2. Expiry check
        if is_asset_expired(asset):
            reasons.append({
                "reason": "Asset Expired",
                "expected": "Valid (Not Expired)",
                "actual": asset.expiry_date.isoformat() if asset.expiry_date else "Expired"
            })
            is_compatible = False

        # 3. Open Maintenance
        if asset.asset_id in open_maint_asset_ids:
            reasons.append({
                "reason": "Open Maintenance",
                "expected": "No active maintenance ticket",
                "actual": "Ticket pending resolution"
            })
            is_compatible = False

        # 4. Asset Type Match
        if location.required_asset_type:
            if not asset.asset_type:
                reasons.append({
                    "reason": "Asset Type Mismatch",
                    "expected": location.required_asset_type,
                    "actual": "Unspecified"
                })
                is_compatible = False
            elif location.required_asset_type.strip().lower() != asset.asset_type.strip().lower():
                reasons.append({
                    "reason": "Asset Type Mismatch",
                    "expected": location.required_asset_type,
                    "actual": asset.asset_type
                })
                is_compatible = False

        # 5. Capacity Match
        if location.required_capacity:
            if not asset.capacity:
                reasons.append({
                    "reason": "Capacity Mismatch",
                    "expected": location.required_capacity,
                    "actual": "Unspecified"
                })
                is_compatible = False
            elif location.required_capacity.strip().lower() != asset.capacity.strip().lower():
                reasons.append({
                    "reason": "Capacity Mismatch",
                    "expected": location.required_capacity,
                    "actual": asset.capacity
                })
                is_compatible = False

        # 6. Already assigned to THIS location
        if asset.location_id == location_id:
            reasons.append({
                "reason": "Already Assigned",
                "expected": "Unassigned or different location",
                "actual": f"Currently assigned to this location ({location_id})"
            })
            is_compatible = False

        # 7. Location Full Capacity (if adding a new asset)
        if location.remaining_capacity <= 0 and asset.location_id != location_id:
            reasons.append({
                "reason": "Location Full",
                "expected": f"Max {location.max_assets} assets",
                "actual": f"Current {location.current_assets_count} assets"
            })
            is_compatible = False

        asset_info = {
            "asset_id": asset.asset_id,
            "serial_number": asset.serial_number or "",
            "asset_type": asset.asset_type or "Unknown",
            "capacity": asset.capacity or "Unknown",
            "status": asset.status,
            "current_location_id": asset.location_id,
            "current_location_name": asset.location.location_name if asset.location else None,
            "is_unassigned": asset.location_id is None,
            "is_reassignment": asset.location_id is not None and asset.location_id != location_id,
            "expiry_date": asset.expiry_date.isoformat() if asset.expiry_date else None,
        }

        if is_compatible:
            compatible.append(asset_info)
        else:
            asset_info["rejection_reasons"] = reasons
            rejected.append(asset_info)

    # Sort compatible: unassigned first, then by asset_id
    compatible.sort(key=lambda a: (0 if a["is_unassigned"] else 1, a["asset_id"]))

    return create_api_response(True, "Compatible assets evaluated successfully", {
        "location": {
            "location_id": location.location_id,
            "location_name": location.location_name,
            "plant": location.plant,
            "area": location.area,
            "department": location.department,
            "building": location.building,
            "floor": location.floor,
            "required_asset_type": location.required_asset_type,
            "required_capacity": location.required_capacity,
            "max_assets": location.max_assets,
            "current_assets_count": location.current_assets_count,
            "remaining_capacity": location.remaining_capacity,
        },
        "currently_assigned": [
            {
                "asset_id": a.asset_id,
                "serial_number": a.serial_number or "",
                "asset_type": a.asset_type or "Unknown",
                "capacity": a.capacity or "Unknown",
                "status": a.status,
                "expiry_date": a.expiry_date.isoformat() if a.expiry_date else None
            } for a in assigned_assets
        ],
        "compatible": compatible,
        "rejected": rejected
    })


@router.post("/{location_id}/assign-asset/{asset_id}")
def assign_asset_to_location_from_location(
    location_id: str,
    asset_id: str,
    payload: Optional[schemas.AssetAssignRequest] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("assign_asset")),
):
    """
    Bidirectional assignment entry point: Assigns an asset to a location from the location side.
    Reuses the exact same validate_asset_assignment and perform_asset_assignment services.
    """
    from ..services.asset_service import validate_asset_assignment, perform_asset_assignment

    if payload is None:
        payload = schemas.AssetAssignRequest()

    can_assign, errors, warnings = validate_asset_assignment(
        db, asset_id, location_id, force=payload.force
    )

    if not can_assign:
        requires_confirm = len(errors) == 0 and len(warnings) > 0
        asset_obj = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "message": "Asset assignment validation failed",
                "errors": errors,
                "warnings": warnings,
                "requires_confirmation": requires_confirm,
                "current_location": asset_obj.location_id if asset_obj else None,
                "target_location": location_id,
            },
        )

    result = perform_asset_assignment(
        db=db,
        asset_id=asset_id,
        location_id=location_id,
        changed_by=current_user.email,
        movement_type=payload.movement_type or "Assignment",
        movement_reason=payload.movement_reason or "Assigned from Locations Page",
        comments=payload.comments,
    )

    create_audit_log(
        db,
        current_user.id,
        "ASSIGN",
        "assets",
        asset_id,
        new_values={"location": location_id},
    )
    db.commit()

    return create_api_response(True, "Asset assigned successfully", {**result, "warnings": warnings})
