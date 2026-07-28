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

router = APIRouter()


def create_api_response(success: bool, message: str, data=None, errors=None) -> dict:
    return {"success": success, "message": message, "data": data, "errors": errors}


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

    # Auto-generate location_id if not provided by client
    location_id = location.location_id or f"LOC-{uuid.uuid4().hex[:8].upper()}"

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

    loc_data = location.model_dump(exclude={"location_id"})
    new_location = models.Location(
        **loc_data, location_id=location_id, created_by_id=current_user.id
    )

    if new_location.qr_code == False:
        new_location.qr_code = location_id

    try:
        db.add(new_location)
        db.commit()
        db.refresh(new_location)
    except exc.IntegrityError as e:
        db.rollback()
        if "uq_location_name_plant" in str(e):
            raise HTTPException(
                status_code=400,
                detail=f"Location name '{location.location_name}' already exists in plant '{location.plant}'",
            )
        raise HTTPException(status_code=400, detail="Database integrity error")

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
