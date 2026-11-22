"""
Assets router — CRUD, assignment validation, history, photo upload.
"""

import os
import io
import base64
from datetime import datetime, date
from typing import Any, List, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.config import settings
from ..core import database
from ..core import dependencies as auth
from ..services.asset_service import (
    perform_asset_assignment,
    unlink_asset_from_location,
    validate_asset_assignment,
)
from ..utils import create_audit_log, generate_qr_code_image, model_to_dict, validate_and_sanitize_image
from .locations import generate_system_id
from ..core.scope import apply_scope, check_record_scope, get_user_scope

router = APIRouter()

def create_api_response(
    success: bool, message: str, data: Optional[Any] = None, errors: Optional[Any] = None
) -> dict:
    return {"success": success, "message": message, "data": data, "errors": errors}


# ─── Master Data Validator & Date Helpers for Asset Bulk Upload ───────────────
class AssetMasterValidator:
    def __init__(self, db: Session):
        self.db = db
        # Active Asset Types
        asset_types = db.query(models.MasterAssetType).filter(models.MasterAssetType.is_active == True).all()
        self.asset_map = {at.name.strip().lower(): at.id for at in asset_types if at.name}
        self.asset_names = [at.name.strip() for at in asset_types if at.name]
        
        # Active Capacities
        capacities = db.query(models.MasterCapacityType).filter(models.MasterCapacityType.is_active == True).all()
        self.cap_map = {c.name.strip().lower(): c.id for c in capacities if c.name}
        self.cap_names = [c.name.strip() for c in capacities if c.name]

        # Locations (map by ID and by Name)
        locations = db.query(models.Location).all()
        self.location_id_map = {l.location_id.strip().lower(): l for l in locations if l.location_id}
        self.location_name_map = {l.location_name.strip().lower(): l for l in locations if l.location_name}

    def resolve_asset_type(self, val: str):
        if not val or not str(val).strip():
            return None, "Asset Type is required"
        val_clean = str(val).strip().lower()
        type_id = self.asset_map.get(val_clean)
        if not type_id:
            valid_opts = ", ".join(self.asset_names) if self.asset_names else "None configured"
            return None, f"Invalid Asset Type '{val}'. Must be one of: {valid_opts}"
        return type_id, None

    def resolve_capacity(self, val: str):
        if not val or not str(val).strip():
            return None, "Capacity is required"
        val_clean = str(val).strip().lower()
        cap_id = self.cap_map.get(val_clean)
        if not cap_id:
            valid_opts = ", ".join(self.cap_names) if self.cap_names else "None configured"
            return None, f"Invalid Capacity '{val}'. Must be one of: {valid_opts}"
        return cap_id, None

    def resolve_location(self, val: str):
        if not val or not str(val).strip():
            return None, None
        val_clean = str(val).strip().lower()
        loc = self.location_id_map.get(val_clean) or self.location_name_map.get(val_clean)
        if not loc:
            return None, f"Location '{val}' not found in system"
        return loc, None


def parse_excel_date(val):
    if val is None or str(val).strip() == "":
        return None, None
    if isinstance(val, (datetime, date)):
        d = val.date() if isinstance(val, datetime) else val
        return d, None
    val_str = str(val).strip()
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(val_str, fmt).date()
            return parsed, None
        except ValueError:
            pass
    return None, f"Invalid date '{val_str}'. Expected format YYYY-MM-DD"


def map_asset_headers(headers):
    mapping = {}
    aliases = {
        "serial_number": ["serial number", "serial_number", "serial", "serial no", "serial #", "sl no"],
        "asset_type": ["asset type", "asset_type", "type", "required asset type", "asset"],
        "capacity": ["capacity", "required capacity", "size"],
        "manufacturer": ["manufacturer", "make", "brand", "mfg"],
        "model": ["model", "model no", "model number"],
        "manufacturing_date": ["manufacturing date", "manufacturing_date", "mfg date", "mfg_date", "manufacture date"],
        "installation_date": ["installation date", "installation_date", "install date", "install_date", "refill date", "refill_date"],
        "expiry_date": ["expiry date", "expiry_date", "expiration date", "expiry", "exp date"],
        "status": ["status", "asset status"],
        "location": ["location", "location id", "location_id", "location name"],
        "remarks": ["remarks", "comment", "comments", "notes", "description"]
    }
    
    for idx, h in enumerate(headers):
        if not h:
            continue
        h_clean = str(h).strip().lower()
        for key, alt_list in aliases.items():
            if key not in mapping and (h_clean == key or h_clean in alt_list):
                mapping[key] = idx
                break
    return mapping


# ─── Bulk Upload Endpoints (Must be registered before /{asset_id}) ───────────
@router.get("/bulk-upload/sample")
def download_asset_bulk_upload_sample(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_assets")),
):
    """
    Generates and downloads the official Asset Bulk Upload Excel template.
    Includes active master data dropdown validations for Asset Type, Capacity, and Status.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Assets Upload Template"

    headers = [
        "Serial Number",
        "Asset Type",
        "Capacity",
        "Manufacturer",
        "Model",
        "Manufacturing Date",
        "Installation Date",
        "Expiry Date",
        "Status",
        "Location",
        "Remarks"
    ]
    ws.append(headers)

    header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for col_idx, cell in enumerate(ws[1], 1):
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = 24
    ws.row_dimensions[1].height = 28

    # Fetch active master data for dropdowns
    active_types = [t.name.strip() for t in db.query(models.MasterAssetType).filter(models.MasterAssetType.is_active == True).all() if t.name]
    active_caps = [c.name.strip() for c in db.query(models.MasterCapacityType).filter(models.MasterCapacityType.is_active == True).all() if c.name]
    sample_type = active_types[0] if active_types else "ABC"
    sample_cap = active_caps[0] if active_caps else "6kg"
    second_type = active_types[1] if len(active_types) > 1 else sample_type
    second_cap = active_caps[1] if len(active_caps) > 1 else sample_cap

    # Realistic sample rows
    sample_rows = [
        ["SN-ABC-9001", sample_type, sample_cap, "Ceasefire", "Pro-Safe", "2024-01-15", "2024-01-20", "2029-01-15", "Active", "", "Main assembly hall line 1"],
        ["SN-CO2-9002", second_type, second_cap, "Amerex", "Carbon-Guard", "2024-03-10", "2024-03-15", "2029-03-10", "Active", "", "Server room electrical safety"]
    ]
    for r in sample_rows:
        ws.append(r)

    # Style sample rows
    for row in ws.iter_rows(min_row=2, max_row=3, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.font = Font(name="Calibri", size=10)
            cell.alignment = Alignment(vertical="center")
            cell.border = thin_border
        ws.row_dimensions[row[0].row].height = 20

    # Add openpyxl Data Validations for Dropdowns
    if active_types:
        dv_type = DataValidation(type="list", formula1=f'"{",".join(active_types)}"', allow_blank=True)
        dv_type.error = "Select a valid Asset Type from the active list"
        dv_type.errorTitle = "Invalid Asset Type"
        ws.add_data_validation(dv_type)
        dv_type.add(f"B2:B500")

    if active_caps:
        dv_cap = DataValidation(type="list", formula1=f'"{",".join(active_caps)}"', allow_blank=True)
        dv_cap.error = "Select a valid Capacity from the active list"
        dv_cap.errorTitle = "Invalid Capacity"
        ws.add_data_validation(dv_cap)
        dv_cap.add(f"C2:C500")

    dv_status = DataValidation(type="list", formula1='"Active,Under Maintenance,Expired,Retired,Draft"', allow_blank=True)
    dv_status.error = "Select a valid Status (Active, Under Maintenance, Expired, Retired, Draft)"
    dv_status.errorTitle = "Invalid Status"
    ws.add_data_validation(dv_status)
    dv_status.add(f"I2:I500")

    # Add Instructions Sheet
    ws_notes = wb.create_sheet(title="Instructions")
    ws_notes.column_dimensions["A"].width = 30
    ws_notes.column_dimensions["B"].width = 75
    ws_notes.append(["Field Name", "Requirement / Description"])
    for cell in ws_notes[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill

    instructions = [
        ("Serial Number", "Required. Unique identifier stamped on the cylinder. Must be unique."),
        ("Asset Type", "Required. Must match active Asset Types (e.g. ABC, CO2, Water)."),
        ("Capacity", "Required. Must match active Capacities (e.g. 6kg, 4.5kg, 9L)."),
        ("Manufacturer", "Optional. Brand/Maker name (e.g. Ceasefire, Amerex, Safex)."),
        ("Model", "Optional. Product model name or code."),
        ("Manufacturing Date", "Optional. Date format: YYYY-MM-DD (e.g. 2024-01-15)."),
        ("Installation Date", "Optional. Installation or refill date in YYYY-MM-DD format."),
        ("Expiry Date", "Optional. Cylinder expiry/hydro-test due date in YYYY-MM-DD format."),
        ("Status", "Optional. Defaults to Active. Allowed: Active, Under Maintenance, Expired, Retired, Draft."),
        ("Location", "Optional. Location ID or Name if you wish to immediately assign the asset."),
        ("Remarks", "Optional. Specific installation or safety remarks.")
    ]
    for field, desc in instructions:
        ws_notes.append([field, desc])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Asset_Bulk_Upload_Sample.xlsx"'}
    )


@router.post("/bulk-upload/preview")
def preview_bulk_upload_assets(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_asset")),
):
    """
    Parses and validates the uploaded Excel file row by row without committing to the database.
    Detects required fields, master data mismatches, and duplicates (in DB and within file).
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload an Excel file (.xlsx, .xls)"
        )

    try:
        contents = file.file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse Excel workbook: {str(e)}")

    row_headers = [cell.value for cell in ws[1] if cell.value is not None]
    if not row_headers:
        raise HTTPException(status_code=400, detail="The uploaded sheet is completely empty")

    header_map = map_asset_headers(row_headers)
    if "serial_number" not in header_map or "asset_type" not in header_map:
        raise HTTPException(
            status_code=400,
            detail="Invalid Excel Template. Sheet must contain at least 'Serial Number' and 'Asset Type' columns."
        )

    validator = AssetMasterValidator(db)
    existing_serials = {s.lower() for (s,) in db.query(models.Asset.serial_number).all() if s}
    occupied_loc_ids = {a[0] for a in db.query(models.Asset.location_id).filter(models.Asset.location_id.isnot(None)).all() if a[0]}
    seen_file_serials = set()
    seen_file_locs = set()

    preview_rows = []
    valid_count = 0
    invalid_count = 0
    duplicate_count = 0

    def get_cell_val(row_cells, field_key):
        idx = header_map.get(field_key)
        if idx is not None and idx < len(row_cells):
            val = row_cells[idx].value
            return val if val is not None else ""
        return ""

    for row_idx, row_cells in enumerate(ws.iter_rows(min_row=2), start=2):
        cell_vals = [cell.value for cell in row_cells]
        if all(v is None or str(v).strip() == "" for v in cell_vals):
            continue

        errors = []
        is_duplicate = False

        serial_raw = get_cell_val(row_cells, "serial_number")
        serial_str = str(serial_raw).strip() if serial_raw != "" else ""

        asset_type_raw = get_cell_val(row_cells, "asset_type")
        asset_type_str = str(asset_type_raw).strip() if asset_type_raw != "" else ""

        cap_raw = get_cell_val(row_cells, "capacity")
        cap_str = str(cap_raw).strip() if cap_raw != "" else ""

        mfg_str = str(get_cell_val(row_cells, "manufacturer")).strip()
        model_str = str(get_cell_val(row_cells, "model")).strip()

        mfg_date_raw = get_cell_val(row_cells, "manufacturing_date")
        inst_date_raw = get_cell_val(row_cells, "installation_date")
        exp_date_raw = get_cell_val(row_cells, "expiry_date")

        status_raw = str(get_cell_val(row_cells, "status")).strip()
        loc_raw = str(get_cell_val(row_cells, "location")).strip()
        remarks_str = str(get_cell_val(row_cells, "remarks")).strip()

        # 1. Serial Number Validation & Duplicate Detection
        if not serial_str:
            errors.append("Serial Number is required")
        else:
            serial_norm = serial_str.lower()
            if serial_norm in existing_serials:
                is_duplicate = True
                errors.append(f"Serial Number '{serial_str}' already exists in database")
            elif serial_norm in seen_file_serials:
                is_duplicate = True
                errors.append(f"Duplicate Serial Number '{serial_str}' found within upload file")
            else:
                seen_file_serials.add(serial_norm)

        # 2. Master Data Asset Type Validation
        type_id, type_err = validator.resolve_asset_type(asset_type_str)
        if type_err:
            errors.append(type_err)

        # 3. Master Data Capacity Validation
        cap_id, cap_err = validator.resolve_capacity(cap_str)
        if cap_err:
            errors.append(cap_err)

        # 4. Dates Validation
        mfg_d, mfg_err = parse_excel_date(mfg_date_raw)
        if mfg_err:
            errors.append(f"Manufacturing Date: {mfg_err}")

        inst_d, inst_err = parse_excel_date(inst_date_raw)
        if inst_err:
            errors.append(f"Installation Date: {inst_err}")

        exp_d, exp_err = parse_excel_date(exp_date_raw)
        if exp_err:
            errors.append(f"Expiry Date: {exp_err}")

        if mfg_d and exp_d and exp_d < mfg_d:
            errors.append("Expiry Date cannot be earlier than Manufacturing Date")

        # 5. Status Validation
        valid_statuses = ["Active", "Under Maintenance", "Expired", "Retired", "Draft"]
        status_clean = "Active"
        if status_raw:
            matched_status = next((s for s in valid_statuses if s.lower() == status_raw.lower()), None)
            if not matched_status:
                errors.append(f"Invalid Status '{status_raw}'. Must be one of: {', '.join(valid_statuses)}")
            else:
                status_clean = matched_status

        # 6. Location Validation (Optional)
        resolved_loc = None
        if loc_raw:
            resolved_loc, loc_err = validator.resolve_location(loc_raw)
            if loc_err:
                errors.append(loc_err)
            elif resolved_loc:
                if resolved_loc.location_id in occupied_loc_ids:
                    errors.append(f"Location '{resolved_loc.location_name}' ({resolved_loc.location_id}) already has an asset assigned (each location can hold 1 asset)")
                elif resolved_loc.location_id in seen_file_locs:
                    errors.append(f"Duplicate Location '{resolved_loc.location_id}' in upload file (each location can hold 1 asset)")
                else:
                    seen_file_locs.add(resolved_loc.location_id)

        # Determine Row Status
        if is_duplicate:
            row_status = "DUPLICATE"
            duplicate_count += 1
        elif errors:
            row_status = "INVALID"
            invalid_count += 1
        else:
            row_status = "VALID"
            valid_count += 1

        preview_rows.append({
            "row_number": row_idx,
            "serial_number": serial_str,
            "asset_type": asset_type_str,
            "capacity": cap_str,
            "manufacturer": mfg_str,
            "model": model_str,
            "manufacturing_date": mfg_d.isoformat() if mfg_d else "",
            "installation_date": inst_d.isoformat() if inst_d else "",
            "expiry_date": exp_d.isoformat() if exp_d else "",
            "status": status_clean,
            "location": loc_raw,
            "location_id": resolved_loc.location_id if resolved_loc else "",
            "remarks": remarks_str,
            "status_code": row_status,
            "status": row_status,
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
def bulk_upload_assets(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_asset")),
):
    """
    Imports all valid assets from the uploaded Excel sheet.
    Automatically generates Asset IDs, QR codes, creates audit logs, and handles failed rows.
    """
    import logging
    logger = logging.getLogger(__name__)

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload an Excel file (.xlsx, .xls)"
        )

    try:
        contents = file.file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel workbook: {str(e)}")

    row_headers = [cell.value for cell in ws[1] if cell.value is not None]
    if not row_headers:
        raise HTTPException(status_code=400, detail="The uploaded sheet is completely empty")

    header_map = map_asset_headers(row_headers)
    if "serial_number" not in header_map or "asset_type" not in header_map:
        raise HTTPException(
            status_code=400,
            detail="Invalid Excel Template. Sheet must contain at least 'Serial Number' and 'Asset Type' columns."
        )

    validator = AssetMasterValidator(db)
    existing_serials = {s.lower() for (s,) in db.query(models.Asset.serial_number).all() if s}
    occupied_loc_ids = {a[0] for a in db.query(models.Asset.location_id).filter(models.Asset.location_id.isnot(None)).all() if a[0]}
    seen_file_serials = set()
    seen_file_locs = set()

    imported = 0
    failed = 0
    duplicates = 0
    skipped = 0
    total_rows = 0

    failed_rows = []
    expected_headers = [
        "Serial Number", "Asset Type", "Capacity", "Manufacturer", "Model",
        "Manufacturing Date", "Installation Date", "Expiry Date", "Status", "Location", "Remarks"
    ]

    def get_cell_val(row_cells, field_key):
        idx = header_map.get(field_key)
        if idx is not None and idx < len(row_cells):
            val = row_cells[idx].value
            return val if val is not None else ""
        return ""

    for row_idx, row_cells in enumerate(ws.iter_rows(min_row=2), start=2):
        cell_vals = [cell.value for cell in row_cells]
        if all(v is None or str(v).strip() == "" for v in cell_vals):
            continue

        total_rows += 1
        errors = []
        is_duplicate = False

        serial_raw = get_cell_val(row_cells, "serial_number")
        serial_str = str(serial_raw).strip() if serial_raw != "" else ""

        asset_type_raw = get_cell_val(row_cells, "asset_type")
        asset_type_str = str(asset_type_raw).strip() if asset_type_raw != "" else ""

        cap_raw = get_cell_val(row_cells, "capacity")
        cap_str = str(cap_raw).strip() if cap_raw != "" else ""

        mfg_str = str(get_cell_val(row_cells, "manufacturer")).strip()
        model_str = str(get_cell_val(row_cells, "model")).strip()

        mfg_date_raw = get_cell_val(row_cells, "manufacturing_date")
        inst_date_raw = get_cell_val(row_cells, "installation_date")
        exp_date_raw = get_cell_val(row_cells, "expiry_date")

        status_raw = str(get_cell_val(row_cells, "status")).strip()
        loc_raw = str(get_cell_val(row_cells, "location")).strip()
        remarks_str = str(get_cell_val(row_cells, "remarks")).strip()

        # 1. Serial Number Validation
        if not serial_str:
            errors.append("Serial Number is required")
        else:
            serial_norm = serial_str.lower()
            if serial_norm in existing_serials:
                is_duplicate = True
                errors.append(f"Serial Number '{serial_str}' already exists in database")
            elif serial_norm in seen_file_serials:
                is_duplicate = True
                errors.append(f"Duplicate Serial Number '{serial_str}' found within upload file")
            else:
                seen_file_serials.add(serial_norm)

        # 2. Master Data Asset Type
        type_id, type_err = validator.resolve_asset_type(asset_type_str)
        if type_err:
            errors.append(type_err)

        # 3. Master Data Capacity
        cap_id, cap_err = validator.resolve_capacity(cap_str)
        if cap_err:
            errors.append(cap_err)

        # 4. Dates
        mfg_d, mfg_err = parse_excel_date(mfg_date_raw)
        if mfg_err:
            errors.append(f"Manufacturing Date: {mfg_err}")

        inst_d, inst_err = parse_excel_date(inst_date_raw)
        if inst_err:
            errors.append(f"Installation Date: {inst_err}")

        exp_d, exp_err = parse_excel_date(exp_date_raw)
        if exp_err:
            errors.append(f"Expiry Date: {exp_err}")

        if mfg_d and exp_d and exp_d < mfg_d:
            errors.append("Expiry Date cannot be earlier than Manufacturing Date")

        # 5. Status
        valid_statuses = ["Active", "Under Maintenance", "Expired", "Retired", "Draft"]
        status_clean = "Active"
        if status_raw:
            matched_status = next((s for s in valid_statuses if s.lower() == status_raw.lower()), None)
            if not matched_status:
                errors.append(f"Invalid Status '{status_raw}'")
            else:
                status_clean = matched_status

        # 6. Location
        resolved_loc = None
        if loc_raw:
            resolved_loc, loc_err = validator.resolve_location(loc_raw)
            if loc_err:
                errors.append(loc_err)
            elif resolved_loc:
                if resolved_loc.location_id in occupied_loc_ids:
                    errors.append(f"Location '{resolved_loc.location_name}' ({resolved_loc.location_id}) already has an asset assigned (each location can hold 1 asset)")
                elif resolved_loc.location_id in seen_file_locs:
                    errors.append(f"Duplicate Location '{resolved_loc.location_id}' in upload file (each location can hold 1 asset)")
                else:
                    seen_file_locs.add(resolved_loc.location_id)

        # Handle Failures / Duplicates
        if is_duplicate:
            duplicates += 1
            skipped += 1
            failed_rows.append([
                serial_str, asset_type_str, cap_str, mfg_str, model_str,
                mfg_d.isoformat() if mfg_d else "",
                inst_d.isoformat() if inst_d else "",
                exp_d.isoformat() if exp_d else "",
                status_clean, loc_raw, remarks_str,
                "; ".join(errors)
            ])
            continue

        if errors:
            failed += 1
            skipped += 1
            failed_rows.append([
                serial_str, asset_type_str, cap_str, mfg_str, model_str,
                mfg_d.isoformat() if mfg_d else "",
                inst_d.isoformat() if inst_d else "",
                exp_d.isoformat() if exp_d else "",
                status_clean, loc_raw, remarks_str,
                "; ".join(errors)
            ])
            continue

        # Valid Record Creation
        try:
            target_plant = resolved_loc.plant if resolved_loc else None
            system_asset_id = generate_system_id(db, "asset", target_plant)

            # Combined remarks
            remarks_parts = []
            if model_str:
                remarks_parts.append(f"Model: {model_str}")
            if remarks_str:
                remarks_parts.append(remarks_str)
            final_remarks = ". ".join(remarks_parts) if remarks_parts else None

            new_asset = models.Asset(
                asset_id=system_asset_id,
                serial_number=serial_str,
                asset_type_id=type_id,
                capacity_id=cap_id,
                manufacturer=mfg_str or None,
                manufacturing_date=mfg_d,
                refill_date=inst_d,
                expiry_date=exp_d,
                status=status_clean,
                remarks=final_remarks,
                barcode=system_asset_id,
                location_id=resolved_loc.location_id if resolved_loc else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_asset)
            db.flush()

            # Generate QR Image
            try:
                generate_qr_code_image(system_asset_id, system_asset_id)
            except Exception as qr_ex:
                logger.warning(f"Failed to generate QR for asset {system_asset_id}: {qr_ex}")

            # If location was assigned, add AssetHistory
            if resolved_loc:
                db.add(models.AssetHistory(
                    asset_id=system_asset_id,
                    old_location_id=None,
                    new_location_id=resolved_loc.location_id,
                    movement_type="Initial Assignment",
                    movement_reason="Asset Bulk Upload Assignment",
                    changed_by=current_user.email,
                    movement_date=datetime.utcnow(),
                ))

            # Audit Log
            create_audit_log(
                db,
                current_user.id,
                "CREATE",
                "assets",
                system_asset_id,
                new_values={
                    "serial_number": serial_str,
                    "asset_type_id": type_id,
                    "capacity_id": cap_id,
                    "location_id": resolved_loc.location_id if resolved_loc else None
                }
            )

            db.commit()
            existing_serials.add(serial_str.lower())
            if resolved_loc:
                occupied_loc_ids.add(resolved_loc.location_id)
            imported += 1

        except Exception as insert_err:
            db.rollback()
            logger.error(f"Failed to insert asset row {row_idx}: {insert_err}")
            failed += 1
            skipped += 1
            failed_rows.append([
                serial_str, asset_type_str, cap_str, mfg_str, model_str,
                mfg_d.isoformat() if mfg_d else "",
                inst_d.isoformat() if inst_d else "",
                exp_d.isoformat() if exp_d else "",
                status_clean, loc_raw, remarks_str,
                f"Database insertion error: {str(insert_err)}"
            ])

    db.commit()

    # Generate error report workbook if any rows failed or were duplicates
    error_report_base64 = None
    if failed_rows:
        error_wb = openpyxl.Workbook()
        error_ws = error_wb.active
        error_ws.title = "Failed Assets"

        error_headers = expected_headers + ["Error Details"]
        error_ws.append(error_headers)

        err_header_fill = PatternFill(start_color="D9EDF7", end_color="D9EDF7", fill_type="solid")
        err_header_font = Font(name="Calibri", bold=True)
        for col_num, cell in enumerate(error_ws[1], 1):
            cell.fill = err_header_fill
            cell.font = err_header_font
            error_ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 24

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



@router.get("", response_model=schemas.APIResponse[schemas.PaginatedAssetResponse])
def get_assets(
    skip: int = 0,
    limit: int = 200,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    unassigned_only: bool = False,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_assets")),
):
    query = apply_scope(db.query(models.Asset), current_user, db, models.Asset)
    if asset_type:
        query = query.filter(models.Asset.asset_type == asset_type)
    if status:
        query = query.filter(models.Asset.status == status)
    if unassigned_only:
        query = query.filter(models.Asset.location_id.is_(None))
    
    items = query.order_by(models.Asset.asset_id).offset(skip).limit(limit).all()
    total = query.count()
    return create_api_response(True, "Assets retrieved successfully", {"items": items, "total": total})


@router.get("/{asset_id}", response_model=schemas.APIResponse[schemas.AssetResponse])
def get_asset(
    asset_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_assets")),
):
    asset = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
    if not asset or not check_record_scope(asset, current_user, db):
        raise HTTPException(status_code=404, detail="Asset not found")
    return create_api_response(True, "Asset retrieved", asset)


@router.get("/by-qr/{qr_code}")
def get_asset_by_qr(
    qr_code: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_assets")),
):
    """
    Fetch comprehensive asset, location, and inspection data by QR code.
    QR code can match asset_id, serial_number, or barcode.
    """
    asset = (
        db.query(models.Asset)
        .filter(
            (models.Asset.asset_id == qr_code)
            | (models.Asset.serial_number == qr_code)
            | (models.Asset.barcode == qr_code)
        )
        .first()
    )
    if not asset or not check_record_scope(asset, current_user, db):
        raise HTTPException(status_code=404, detail=f"No asset found for QR '{qr_code}'")

    location = None
    if asset.location_id:
        location = db.query(models.Location).filter(models.Location.location_id == asset.location_id).first()

    last_inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.asset_id == asset.asset_id)
        .order_by(models.Inspection.inspection_date.desc())
        .first()
    )

    from datetime import timedelta

    last_date = last_inspection.inspection_date if last_inspection else None
    freq = asset.inspection_frequency or (location.inspection_frequency if location else 30)
    next_due = (last_date + timedelta(days=freq)) if last_date else None

    return create_api_response(True, "Asset fetched by QR", {
        "asset": {
            "asset_id": asset.asset_id,
            "asset_type": asset.asset_type,
            "capacity": asset.capacity,
            "manufacturer": asset.manufacturer,
            "serial_number": asset.serial_number,
            "barcode": asset.barcode,
            "manufacturing_date": asset.manufacturing_date,
            "refill_date": asset.refill_date,
            "expiry_date": asset.expiry_date,
            "status": asset.status,
            "inspection_frequency": freq
        },
        "location": {
            "location_id": location.location_id if location else None,
            "location_name": location.location_name if location else None,
            "plant": location.plant if location else None,
            "department": location.department if location else None
        } if location else None,
        "inspection": {
            "last_inspection_date": last_date,
            "next_inspection_due": next_due,
            "overall_status": last_inspection.overall_status if last_inspection else None
        }
    })


@router.post("", response_model=schemas.APIResponse[schemas.AssetResponse], status_code=201)
def create_asset(
    asset: schemas.AssetCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_asset")),
):
    import uuid

    # Auto-generate asset_id if not provided by client
    asset_id = asset.asset_id or f"AST-{uuid.uuid4().hex[:8].upper()}"

    existing = (
        db.query(models.Asset)
        .filter(
            (models.Asset.asset_id == asset_id)
            | (models.Asset.serial_number == asset.serial_number)
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Asset ID or Serial Number already registered"
        )

    asset_data = asset.model_dump(exclude={"asset_id"})
    new_asset = models.Asset(**asset_data, asset_id=asset_id)
    new_asset.created_at = datetime.utcnow()
    new_asset.updated_at = datetime.utcnow()
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)

    create_audit_log(db, current_user.id, "CREATE", "assets", asset_id)
    db.commit()
    return create_api_response(True, "Asset created", new_asset)


@router.put("/{asset_id}", response_model=schemas.APIResponse[schemas.AssetResponse])
def update_asset(
    asset_id: str,
    asset: schemas.AssetUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("edit_asset")),
):
    db_asset = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
    if not db_asset or not check_record_scope(db_asset, current_user, db):
        raise HTTPException(status_code=404, detail="Asset not found")

    old_values = model_to_dict(db_asset)
    for key, value in asset.model_dump(exclude_unset=True).items():
        setattr(db_asset, key, value)
    db_asset.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_asset)

    create_audit_log(
        db,
        current_user.id,
        "UPDATE",
        "assets",
        asset_id,
        old_values=old_values,
        new_values=model_to_dict(db_asset),
    )
    db.commit()
    return create_api_response(True, "Asset updated", db_asset)


@router.delete("/{asset_id}")
def delete_asset(
    asset_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("delete_asset")),
):
    db_asset = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
    if not db_asset or not check_record_scope(db_asset, current_user, db):
        raise HTTPException(status_code=404, detail="Asset not found")
    if db_asset.current_location_id:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete assigned asset '{asset_id}'. Unlink from location '{db_asset.current_location_id}' first.",
        )

    active_maint = db.query(models.Maintenance).filter(
        models.Maintenance.asset_id == asset_id,
        models.Maintenance.status.notin_(["Closed", "Verified", "Completed"])
    ).first()
    if active_maint:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete asset '{asset_id}' with active maintenance ticket #{active_maint.maintenance_id}.",
        )

    db.delete(db_asset)
    db.commit()
    create_audit_log(db, current_user.id, "DELETE", "assets", asset_id)
    db.commit()
    return create_api_response(True, f"Asset '{asset_id}' deleted successfully")


# ─── Assignment Endpoints ────────────────────────────────────────────────────
@router.post("/{asset_id}/link/{location_id}")
def link_asset_to_location(
    asset_id: str,
    location_id: str,
    payload: Optional[schemas.AssetAssignRequest] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("assign_asset")),
):
    """
    Assign asset to location with full validation.
    Raises detailed errors for mismatches, expired status, open tickets, etc.
    """
    asset_check = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
    if not asset_check or not check_record_scope(asset_check, current_user, db):
        raise HTTPException(status_code=404, detail="Asset not found")

    loc_check = db.query(models.Location).filter(models.Location.location_id == location_id).first()
    if not loc_check or not check_record_scope(loc_check, current_user, db):
        raise HTTPException(status_code=404, detail="Location not found")

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
        movement_type=payload.movement_type,
        movement_reason=payload.movement_reason,
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

    return create_api_response(True, "Asset assigned", {**result, "warnings": warnings})


@router.delete("/{asset_id}/unlink")
def unlink_asset(
    asset_id: str,
    reason: str = "Manually unlinked",
    movement_type: str = "Transfer",
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("assign_asset")),
):
    asset_check = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
    if not asset_check or not check_record_scope(asset_check, current_user, db):
        raise HTTPException(status_code=404, detail="Asset not found")

    result = unlink_asset_from_location(
        db, asset_id, current_user.email, reason, movement_type
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    create_audit_log(db, current_user.id, "UNLINK", "assets", asset_id)
    db.commit()
    return create_api_response(True, "Asset unlinked", result)

@router.get("/{asset_id}/compatible-locations")
def get_compatible_locations(
    asset_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_locations")),
):
    import logging
    logger = logging.getLogger(__name__)

    asset = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
    if not asset or not check_record_scope(asset, current_user, db):
        raise HTTPException(status_code=404, detail="Asset not found")
        
    locations = apply_scope(
        db.query(models.Location).filter(models.Location.status != "Inactive"),
        current_user,
        db,
        models.Location
    ).all()
    
    current_plant = asset.location.plant if asset.location else ""
    current_area = asset.location.area if asset.location else ""
    
    compatible = []
    rejected = []
    
    for loc in locations:
        reasons = []
        is_compatible = True
        
        # 1. Asset Type Match (only if location specifies a required type)
        if loc.required_asset_type_id and asset.asset_type_id:
            if asset.asset_type_id != loc.required_asset_type_id:
                reasons.append({
                    "reason": "Asset Type Mismatch",
                    "expected": loc.required_asset_type or "Unspecified",
                    "actual": asset.asset_type or "Unspecified"
                })
                is_compatible = False
        elif loc.required_asset_type and asset.asset_type:
            if loc.required_asset_type.strip().lower() != asset.asset_type.strip().lower():
                reasons.append({
                    "reason": "Asset Type Mismatch",
                    "expected": loc.required_asset_type,
                    "actual": asset.asset_type
                })
                is_compatible = False
            
        # 2. Capacity Match (only if location specifies a required capacity)
        if loc.required_capacity_id and asset.capacity_id:
            if asset.capacity_id != loc.required_capacity_id:
                reasons.append({
                    "reason": "Capacity Mismatch",
                    "expected": loc.required_capacity or "Unspecified",
                    "actual": asset.capacity or "Unspecified"
                })
                is_compatible = False
        elif loc.required_capacity and asset.capacity:
            if loc.required_capacity.strip().lower() != asset.capacity.strip().lower():
                reasons.append({
                    "reason": "Capacity Mismatch",
                    "expected": loc.required_capacity,
                    "actual": asset.capacity
                })
                is_compatible = False
            
        # 3. Full Capacity (Max 1 asset per location)
        is_loc_full = loc.current_assets_count >= 1 or loc.remaining_capacity <= 0
        if is_loc_full and asset.current_location_id != loc.location_id:
            reasons.append({
                "reason": "Location Full",
                "expected": "Max 1 asset",
                "actual": f"Currently occupied ({loc.current_assets_count} assets)"
            })
            is_compatible = False
                
        # Debug Logging STEP 8
        print("\n--- COMPATIBILITY CHECK ---")
        print(f"Location ID: {loc.location_id}")
        print(f"Asset Type ID: {asset.asset_type_id} | Location Req Asset ID: {loc.required_asset_type_id}")
        print(f"Capacity ID: {asset.capacity_id} | Location Req Capacity ID: {loc.required_capacity_id}")
        print(f"Remaining Capacity: {loc.remaining_capacity}")
        print(f"Comparison Result: {'MATCH' if is_compatible else 'REJECTED'}")
        if not is_compatible:
            print(f"Reasons: {[r['reason'] for r in reasons]}")

        loc_data = {
            "location_id": loc.location_id,
            "location_name": loc.location_name,
            "plant": loc.plant,
            "area": loc.area,
            "building": loc.building,
            "floor": loc.floor,
            "required_asset_type": loc.required_asset_type,
            "required_capacity": loc.required_capacity,
            "max_assets": loc.max_assets,
            "current_assets_count": loc.current_assets_count,
            "remaining_capacity": loc.remaining_capacity
        }
                
        if is_compatible:
            compatible.append(loc_data)
        else:
            loc_data["rejection_reasons"] = reasons
            rejected.append(loc_data)
            
    # Sort compatible locations
    def sort_key(l):
        same_plant = 1 if l["plant"] == current_plant and current_plant else 0
        same_area = 1 if l["area"] == current_area and current_area else 0
        return (
            same_plant,
            same_area,
            l["remaining_capacity"]
        )
        
    compatible.sort(key=sort_key, reverse=True)
    
    return create_api_response(True, "Compatibility evaluated", {
        "compatible": compatible,
        "rejected": rejected
    })


@router.get("/{asset_id}/history", response_model=schemas.APIResponse[List[schemas.AssetHistoryResponse]])
def get_asset_history(
    asset_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_assets")),
):
    asset = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    history = (
        db.query(models.AssetHistory)
        .filter(models.AssetHistory.asset_id == asset_id)
        .order_by(models.AssetHistory.movement_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return create_api_response(True, "History retrieved", history)
    return create_api_response(True, "History retrieved", history)


@router.post("/{asset_id}/photo")
async def upload_asset_photo(
    asset_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("edit_asset")),
):
    asset = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
    if not asset or not check_record_scope(asset, current_user, db):
        raise HTTPException(status_code=404, detail="Asset not found")

    sanitized_bytes, ext, _ = await validate_and_sanitize_image(file)

    import uuid
    filename = f"asset_{asset_id}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, "photos", filename)
    with open(save_path, "wb") as f:
        f.write(sanitized_bytes)

    asset.photo = f"uploads/photos/{filename}"
    db.commit()
    return create_api_response(True, "Photo uploaded successfully", {"photo_url": asset.photo})
