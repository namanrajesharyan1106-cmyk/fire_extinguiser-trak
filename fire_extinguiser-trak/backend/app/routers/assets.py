"""
Assets router — CRUD, assignment validation, history, photo upload.
"""

import os
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..core import database
from ..core import dependencies as auth
from ..services.asset_service import (
    perform_asset_assignment,
    unlink_asset_from_location,
    validate_asset_assignment,
)
from ..utils import create_audit_log, model_to_dict

router = APIRouter()

def create_api_response(
    success: bool, message: str, data: Optional[Any] = None, errors: Optional[Any] = None
) -> dict:
    return {"success": success, "message": message, "data": data, "errors": errors}


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
    query = db.query(models.Asset)
    if asset_type:
        query = query.filter(models.Asset.asset_type == asset_type)
    if status:
        query = query.filter(models.Asset.status == status)
    if unassigned_only:
        query = query.filter(models.Asset.location_id is None)
    
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
    if not asset:
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
    if not asset:
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
    if not db_asset:
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
    if not db_asset:
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
    result = unlink_asset_from_location(
        db, asset_id, current_user.email, reason, movement_type
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    create_audit_log(db, current_user.id, "UNLINK", "assets", asset_id)
    db.commit()
    return create_api_response(True, "Asset unlinked", result)


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
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_mimes = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_mimes or ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}' or MIME type '{file.content_type}'. Allowed: {list(settings.ALLOWED_EXTENSIONS)}",
        )

    # Check size
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )

    filename = f"asset_{asset_id}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, "photos", filename)
    with open(save_path, "wb") as f:
        f.write(content)

    asset.photo = f"uploads/photos/{filename}"
    db.commit()
    return create_api_response(True, "Photo uploaded successfully", {"photo_url": asset.photo})
