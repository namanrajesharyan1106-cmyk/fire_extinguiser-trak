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
from ..config import settings
from ..core import database
from ..core import dependencies as auth
from ..schemas.base import APIResponse
from ..utils import create_audit_log, generate_qr_code_image
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
    prefix = configs.get(f"{entity_type}_prefix", "LOC") if entity_type == "location" else configs.get(f"{entity_type}_prefix", "")
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
            "plants": [r.name for r in db.query(models.MasterPlant).filter(models.MasterPlant.is_active == True).order_by(models.MasterPlant.name).all() if r.name],
            "areas": [r.name for r in db.query(models.MasterArea).filter(models.MasterArea.is_active == True).order_by(models.MasterArea.name).all() if r.name],
            "depts": [r.name for r in db.query(models.MasterDepartment).filter(models.MasterDepartment.is_active == True).order_by(models.MasterDepartment.name).all() if r.name],
            "buildings": [r.name for r in db.query(models.MasterBuilding).filter(models.MasterBuilding.is_active == True).order_by(models.MasterBuilding.name).all() if r.name],
            "floors": [r.name for r in db.query(models.MasterFloor).filter(models.MasterFloor.is_active == True).order_by(models.MasterFloor.name).all() if r.name],
            "assets": [r.name for r in db.query(models.MasterAssetType).filter(models.MasterAssetType.is_active == True).order_by(models.MasterAssetType.name).all() if r.name],
            "caps": [r.name for r in db.query(models.MasterCapacityType).filter(models.MasterCapacityType.is_active == True).order_by(models.MasterCapacityType.name).all() if r.name]
        }

class LocationMasterValidator:
    def __init__(self, db: Session):
        masters = MasterDataService.get_active_masters(db)
        self.plants = {p.strip().lower() for p in masters["plants"]}
        self.areas = {a.strip().lower() for a in masters["areas"]}
        self.depts = {d.strip().lower() for d in masters["depts"]}
        self.buildings = {b.strip().lower() for b in masters["buildings"]}
        self.floors = {f.strip().lower() for f in masters["floors"]}
        
        self.asset_map = {r.name.strip().lower(): r.id for r in db.query(models.MasterAssetType).filter(models.MasterAssetType.is_active == True).all() if r.name}
        self.cap_map = {r.name.strip().lower(): r.id for r in db.query(models.MasterCapacityType).filter(models.MasterCapacityType.is_active == True).all() if r.name}
        
    def validate_strings(self, plant: str, area: str, department: str, building: str, floor: str) -> list[str]:
        errors = []
        if plant and plant.strip().lower() not in self.plants: errors.append(f"Invalid Plant '{plant}'")
        if area and area.strip().lower() not in self.areas: errors.append(f"Invalid Area '{area}'")
        if department and department.strip().lower() not in self.depts: errors.append(f"Invalid Department '{department}'")
        if building and building.strip().lower() not in self.buildings: errors.append(f"Invalid Building '{building}'")
        if floor and floor.strip().lower() not in self.floors: errors.append(f"Invalid Floor '{floor}'")
        return errors
        
    def resolve_asset_capacity(self, req_asset: str, capacity: str):
        errors = []
        asset_id = self.asset_map.get(req_asset.strip().lower()) if req_asset else None
        cap_id = self.cap_map.get(capacity.strip().lower()) if capacity else None
        
        if req_asset and not asset_id: errors.append(f"Invalid Asset Type '{req_asset}'")
        if capacity and not cap_id: errors.append(f"Invalid Capacity '{capacity}'")
        
        return asset_id, cap_id, errors


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
    query = db.query(models.Location)

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
    current_user: models.User = Depends(auth.require_roles(["ADMIN"]))
):
    """Generate and return a sample Excel file for bulk location upload."""
    from openpyxl.worksheet.datavalidation import DataValidation
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Locations"
    
    ws_instr = wb.create_sheet(title="Instructions")
    ws_instr.append(["Instructions for Bulk Upload"])
    ws_instr.append(["1. Fill out the Locations sheet using the dropdowns provided."])
    ws_instr.append(["2. Do not modify the column headers."])
    ws_instr.append(["3. All fields except 'QR Code Value' are mandatory."])
    ws_instr.append(["4. Duplicate Location IDs or Location Name + Plant combinations will be rejected."])
    ws_instr.append(["5. If a row fails validation, an Error Report will be generated for you to download."])
    
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
    
    headers_master = ["Plant", "Area", "Department", "Building", "Floor", "Required Asset", "Capacity"]
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
        "Required Asset",
        "Capacity",
        "QR Code Value (Optional)"
    ]
    
    ws.append(headers)
    
    ws.append([
        "Assembly Zone A", 
        plants[0] if plants else "PP02", 
        areas[0] if areas else "Assembly", 
        depts[0] if depts else "Production", 
        buildings[0] if buildings else "Main Building", 
        floors[0] if floors else "Ground", 
        assets[0] if assets else "ABC", 
        caps[0] if caps else "8kg", 
        ""
    ])
    
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    for col_num, cell in enumerate(ws[1], 1):
        cell.fill = header_fill
        cell.font = header_font
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 20
        
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
        "Required Asset": (assets, "F"),
        "Capacity": (caps, "G")
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


@router.post("/bulk-upload")
def bulk_upload_locations(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_roles(["ADMIN"]))
):
    import logging
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file (.xlsx)")
        
    try:
        contents = file.file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents))
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
        
    rows = list(ws.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        raise HTTPException(status_code=400, detail="The Excel file is empty or missing data rows.")
        
    expected_headers = [
        "Location Name", "Plant", "Area", "Department", 
        "Building", "Floor", "Required Asset", "Capacity", "QR Code Value (Optional)"
    ]
    
    actual_headers = [str(cell).strip() if cell else "" for cell in rows[0]]
    
    if actual_headers[:9] != expected_headers:
        raise HTTPException(
            status_code=400, 
            detail="Invalid Excel Template",
            headers={"X-Template-Error": "true"}
        )
        
    total_rows = len(rows) - 1
    imported = 0
    failed = 0
    skipped = 0
    
    failed_rows = []
    
    existing_locations = db.query(models.Location.location_id, models.Location.location_name, models.Location.plant, models.Location.qr_code).all()
    existing_ids = {loc.location_id for loc in existing_locations}
    existing_name_plants = {(loc.location_name, loc.plant) for loc in existing_locations}
    existing_qrs = {loc.qr_code for loc in existing_locations if loc.qr_code}
    
    existing_qrs = {loc.qr_code for loc in existing_locations if loc.qr_code}
    
    validator = LocationMasterValidator(db)
    
    for row_idx, row in enumerate(rows[1:], start=2):
        if not any(row):
            skipped += 1
            continue
            
        (
            loc_name, plant, area, department, 
            building, floor, req_asset, capacity, qr_raw
        ) = list(row)[:9] + [None] * max(0, 9 - len(row))
        
        loc_name = str(loc_name).strip() if loc_name else None
        plant = str(plant).strip() if plant else None
        area = str(area).strip() if area else None
        department = str(department).strip() if department else None
        building = str(building).strip() if building else None
        floor = str(floor).strip() if floor else None
        req_asset = str(req_asset).strip() if req_asset else None
        capacity = str(capacity).strip() if capacity else None
        qr_code = str(qr_raw).strip() if qr_raw else None
        
        errors = []
        if not loc_name: errors.append("Location Name is required")
        if not plant: errors.append("Plant is required")
        if not area: errors.append("Area is required")
        if not department: errors.append("Department is required")
        if not building: errors.append("Building is required")
        if not floor: errors.append("Floor is required")
        if not req_asset: errors.append("Required Asset is required")
        if not capacity: errors.append("Capacity is required")
            
        validation_errors = validator.validate_strings(plant, area, department, building, floor)
        errors.extend(validation_errors)
        
        asset_id, cap_id, ac_errors = validator.resolve_asset_capacity(req_asset, capacity)
        errors.extend(ac_errors)

        if loc_name and plant and (loc_name, plant) in existing_name_plants:
            errors.append(f"Location Name '{loc_name}' already exists in Plant '{plant}'")
            
        if qr_code and qr_code in existing_qrs:
            errors.append(f"QR Code '{qr_code}' already exists")

        if errors:
            failed += 1
            failed_row = list(row) + ["; ".join(errors)]
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
            existing_name_plants.add((loc_name, plant))
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
            failed_rows.append(list(row) + [f"Database error: {str(e)}"])
            
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
    if not location:
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
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return create_api_response(True, "Location retrieved", location)


@router.post("", response_model=APIResponse[schemas.LocationResponse], status_code=201)
def create_location(
    location: schemas.LocationCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_location")),
):
    import uuid
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
    if not db_location:
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
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Safe Delete: Prevent deletion if an asset is currently assigned
    asset = getattr(db_location, "assets", None)

    if asset is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete location '{location_id}' because asset '{asset.asset_id}' is assigned. Unlink the asset first.",
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

    if location.qr_code == False:
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

    if location.qr_image_path == False or os.path == False.exists(
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
