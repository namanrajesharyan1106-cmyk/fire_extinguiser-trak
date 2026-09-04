from typing import Any
"""
Inspections router — full checklist, auto-status calculation, multi-photo.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..core import database
from ..core import dependencies as auth
from ..services.inspection_service import process_inspection
from ..utils import auto_calculate_inspection_status, create_audit_log

router = APIRouter()

def create_api_response(
    success: bool, message: str, data: Any = None, errors: Any = None
) -> dict:
    return {"success": success, "message": message, "data": data, "errors": errors}



@router.get("", response_model=schemas.APIResponse[List[schemas.InspectionResponse]])
def get_inspections(
    skip: int = 0,
    limit: int = 100,
    location_id: Optional[str] = None,
    asset_id: Optional[str] = None,
    overall_status: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_inspections")),
):
    query = db.query(models.Inspection)
    if location_id:
        query = query.filter(models.Inspection.location_id == location_id)
    if asset_id:
        query = query.filter(models.Inspection.asset_id == asset_id)
    if overall_status:
        query = query.filter(models.Inspection.overall_status == overall_status)
    inspections = (
        query.order_by(models.Inspection.inspection_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return create_api_response(True, "Inspections retrieved", inspections)


@router.get("/due-today")
def get_inspections_due_today(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_inspections")),
):
    """Return locations where inspection is due today or overdue."""
    today = datetime.utcnow()
    due_locations = []

    locations = (
        db.query(models.Location)
        .filter(
            models.Location.status == "Active",
            models.Location.inspection_frequency is not None,
        )
        .all()
    )

    for loc in locations:
        if loc.last_inspection_date is None:
            # Never inspected — is due
            due_locations.append(
                {
                    "location_id": loc.location_id,
                    "location_name": loc.location_name,
                    "last_inspection": None,
                    "days_overdue": None,
                    "current_asset_id": loc.current_asset_id,
                }
            )
        else:
            next_due = loc.last_inspection_date + timedelta(
                days=loc.inspection_frequency
            )
            if today >= next_due:
                days_overdue = (today - next_due).days
                due_locations.append(
                    {
                        "location_id": loc.location_id,
                        "location_name": loc.location_name,
                        "last_inspection": loc.last_inspection_date.isoformat(),
                        "days_overdue": days_overdue,
                        "current_asset_id": loc.current_asset_id,
                    }
                )

    return {"count": len(due_locations), "locations": due_locations}


@router.get("/by-location-qr/{qr_value}")
def get_inspection_form_data(
    qr_value: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Scan QR → return pre-populated data for the inspection form.
    Returns location info + current asset info.
    """
    location = (
        db.query(models.Location).filter(models.Location.qr_code == qr_value).first()
    )
    if not location:
        raise HTTPException(
            status_code=404, detail=f"No location found for QR code '{qr_value}'"
        )

    asset = None
    if location.current_asset_id:
        asset = (
            db.query(models.Asset)
            .filter(models.Asset.asset_id == location.current_asset_id)
            .first()
        )

    last_inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.location_id == location.location_id)
        .order_by(models.Inspection.inspection_date.desc())
        .first()
    )

    return {
        "location": {
            "location_id": location.location_id,
            "location_name": location.location_name,
            "plant": location.plant,
            "department": location.department,
            "building": location.building,
            "floor": location.floor,
            "area": location.area,
            "risk_category": location.risk_category,
            "required_asset_type": location.required_asset_type,
            "required_capacity": location.required_capacity,
        },
        "asset": (
            {
                "asset_id": asset.asset_id if asset else None,
                "asset_type": asset.asset_type if asset else None,
                "capacity": asset.capacity if asset else None,
                "manufacturer": asset.manufacturer if asset else None,
                "expiry_date": (
                    asset.expiry_date.isoformat()
                    if asset and asset.expiry_date
                    else None
                ),
                "refill_date": (
                    asset.refill_date.isoformat()
                    if asset and asset.refill_date
                    else None
                ),
            }
            if asset
            else None
        ),
        "last_inspection": (
            {
                "inspection_id": (
                    last_inspection.inspection_id if last_inspection else None
                ),
                "date": (
                    last_inspection.inspection_date.isoformat()
                    if last_inspection
                    else None
                ),
                "overall_status": (
                    last_inspection.overall_status if last_inspection else None
                ),
            }
            if last_inspection
            else None
        ),
    }


@router.get("/{inspection_id}", response_model=schemas.APIResponse[schemas.InspectionResponse])
def get_inspection(
    inspection_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_inspections")),
):
    inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.inspection_id == inspection_id)
        .first()
    )
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return create_api_response(True, "Inspection retrieved", inspection)


@router.post("", response_model=schemas.APIResponse[schemas.InspectionResponse], status_code=201)
def create_inspection(
    inspection: schemas.InspectionCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_inspection")),
):
    # Validate location exists
    location = (
        db.query(models.Location)
        .filter(models.Location.location_id == inspection.location_id)
        .first()
    )
    if not location:
        raise HTTPException(
            status_code=404, detail=f"Location '{inspection.location_id}' not found"
        )

    # Use current asset from location if not specified
    asset_id = inspection.asset_id or location.current_asset_id
    if asset_id:
        asset = db.query(models.Asset).filter(models.Asset.asset_id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found")

    # Build checklist dict for status calculation
    checklist = {
        "pressure": inspection.pressure,
        "seal": inspection.seal,
        "pin": inspection.pin,
        "gauge": inspection.gauge,
        "hose": inspection.hose,
        "nozzle": inspection.nozzle,
        "visibility": inspection.visibility,
        "accessibility": inspection.accessibility,
        "mounting": inspection.mounting,
        "safety_tag": inspection.safety_tag,
        "cylinder_damage": inspection.cylinder_damage,
    }

    # Auto-calculate overall status — never trust client input
    overall_status = auto_calculate_inspection_status(checklist)

    # Pop duplicate keys that are being supplied explicitly below
    inspection_data = inspection.model_dump()
    inspection_data.pop("asset_id", None)
    inspection_data.pop("inspector", None)

    import uuid
    inspection_no = f"INS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    new_inspection = models.Inspection(
        **inspection_data,
        asset_id=asset_id,
        inspection_no=inspection_no,
        inspector=inspection.inspector or current_user.name,
        inspector_id=current_user.id,
        overall_status=overall_status,
        inspection_date=datetime.utcnow(),
    )
    db.add(new_inspection)
    db.flush()

    # Post-processing (update location date, auto-maintenance, notifications)
    new_inspection = process_inspection(db, new_inspection, current_user)

    create_audit_log(
        db, current_user.id, "CREATE", "inspection", str(new_inspection.inspection_id)
    )
    db.commit()
    db.refresh(new_inspection)
    return create_api_response(True, "Inspection created", new_inspection)


@router.post("/{inspection_id}/photos")
async def upload_inspection_photos(
    inspection_id: int,
    label: str = "Inspection Evidence",
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_inspection")),
):
    inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.inspection_id == inspection_id)
        .first()
    )
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{ext}'")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    import uuid

    filename = f"insp_{inspection_id}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, "photos", filename)
    with open(save_path, "wb") as f:
        f.write(content)

    attachment = models.Attachment(
        related_id=str(inspection_id),
        related_type="inspection",
        file_path=f"uploads/photos/{filename}",
        file_type=file.content_type,
        label=label,
        uploaded_by=current_user.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return {
        "attachment_id": attachment.id,
        "file_path": attachment.file_path,
        "label": label,
    }


@router.get("/{inspection_id}/photos", response_model=schemas.APIResponse[List[schemas.AttachmentResponse]])
def get_inspection_photos(
    inspection_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_inspections")),
):
    photos = db.query(models.Attachment).filter(models.Attachment.related_type == "inspection", models.Attachment.related_id == str(inspection_id)).all()
    return create_api_response(True, "Photos retrieved", photos)
