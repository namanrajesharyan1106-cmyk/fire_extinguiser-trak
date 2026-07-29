from typing import Any
"""
Maintenance router — 8-stage workflow, technician assignment, evidence photos.
"""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..core import database
from ..core import dependencies as auth
from ..core.constants import MAINTENANCE_TRANSITIONS
from ..core.constants import role_has_permission as _role_has_perm
from ..utils import create_audit_log

router = APIRouter()

def create_api_response(
    success: bool, message: str, data: Any = None, errors: Any = None
) -> dict:
    return {"success": success, "message": message, "data": data, "errors": errors}



@router.get("", response_model=schemas.APIResponse[List[schemas.MaintenanceResponse]])
def get_maintenance_tickets(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    asset_id: Optional[str] = None,
    location_id: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_maintenance")),
):
    query = db.query(models.Maintenance)
    if status:
        query = query.filter(models.Maintenance.status == status)
    if priority:
        query = query.filter(models.Maintenance.priority == priority)
    if asset_id:
        query = query.filter(models.Maintenance.asset_id == asset_id)
    if location_id:
        query = query.filter(models.Maintenance.location_id == location_id)
    tickets = query.order_by(models.Maintenance.opened_date.desc()).offset(skip).limit(limit).all()
    return create_api_response(True, "Maintenance tickets retrieved", tickets)


@router.get("/open")
def get_open_tickets(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_maintenance")),
):
    tickets = (
        db.query(models.Maintenance)
        .filter(models.Maintenance.status.notin_(["Closed", "Verified"]))
        .order_by(models.Maintenance.opened_date.desc())
        .all()
    )
    return create_api_response(True, "Open tickets retrieved", {"count": len(tickets), "tickets": [schemas.MaintenanceResponse.model_validate(t) for t in tickets]})


@router.get("/{ticket_id}", response_model=schemas.APIResponse[schemas.MaintenanceResponse])
def get_ticket(
    ticket_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_maintenance")),
):
    ticket = (
        db.query(models.Maintenance)
        .filter(models.Maintenance.maintenance_id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Maintenance ticket not found")
    return create_api_response(True, "Ticket retrieved", ticket)


@router.post("", response_model=schemas.APIResponse[schemas.MaintenanceResponse], status_code=201)
def create_maintenance_ticket(
    ticket: schemas.MaintenanceCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("create_maintenance")),
):
    if ticket.asset_id:
        asset = (
            db.query(models.Asset)
            .filter(models.Asset.asset_id == ticket.asset_id)
            .first()
        )
        if not asset:
            raise HTTPException(
                status_code=404, detail=f"Asset '{ticket.asset_id}' not found"
            )

    if ticket.location_id:
        location = (
            db.query(models.Location)
            .filter(models.Location.location_id == ticket.location_id)
            .first()
        )
        if not location:
            raise HTTPException(
                status_code=404, detail=f"Location '{ticket.location_id}' not found"
            )



    ticket_data = ticket.model_dump()
    ticket_data.pop("source", None)

    new_ticket = models.Maintenance(
        **ticket_data,
        status="Open",
        opened_date=datetime.utcnow(),
    )
    db.add(new_ticket)
    
    if ticket.asset_id:
        asset = db.query(models.Asset).filter(models.Asset.asset_id == ticket.asset_id).first()
        if asset:
            asset.status = "Under Maintenance"

    
    if ticket.asset_id:
        asset = db.query(models.Asset).filter(models.Asset.asset_id == ticket.asset_id).first()
        if asset:
            asset.status = "Under Maintenance"

    db.commit()
    db.refresh(new_ticket)

    create_audit_log(
        db, current_user.id, "CREATE", "maintenance", str(new_ticket.maintenance_id)
    )
    db.commit()
    return create_api_response(True, "Ticket created", new_ticket)


@router.put("/{ticket_id}", response_model=schemas.APIResponse[schemas.MaintenanceResponse])
def update_maintenance_ticket(
    ticket_id: int,
    update: schemas.MaintenanceUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("edit_maintenance")),
):
    ticket = (
        db.query(models.Maintenance)
        .filter(models.Maintenance.maintenance_id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(ticket, key, value)

    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return create_api_response(True, "Ticket retrieved", ticket)


@router.put("/{ticket_id}/status", response_model=schemas.APIResponse[schemas.MaintenanceResponse])
def update_ticket_status(
    ticket_id: int,
    status_update: schemas.MaintenanceStatusUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("edit_maintenance")),
):
    ticket = (
        db.query(models.Maintenance)
        .filter(models.Maintenance.maintenance_id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Validate transition
    allowed_next = MAINTENANCE_TRANSITIONS.get(ticket.status, [])
    if status_update.new_status not in allowed_next:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid status transition: '{ticket.status}' → '{status_update.new_status}'. "
                f"Allowed next statuses: {allowed_next}"
            ),
        )

    # Special role checks
    if status_update.new_status == "Verified":
        if not _role_has_perm(current_user.role, "verify_maintenance"):
            raise HTTPException(
                status_code=403,
                detail="Only Safety Officers/Heads can verify maintenance",
            )

    if status_update.new_status == "Closed":
        if not _role_has_perm(current_user.role, "close_maintenance"):
            raise HTTPException(
                status_code=403, detail="Only Safety Heads/Admins can close tickets"
            )

    old_status = ticket.status
    ticket.status = status_update.new_status

    if status_update.remarks:
        ticket.remarks = (
            (ticket.remarks or "")
            + f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {status_update.remarks}"
        )

    if status_update.technician_id:
        ticket.technician_id = status_update.technician_id

    if status_update.verified_by:
        ticket.verified_by = status_update.verified_by

    if status_update.new_status == "Completed":
        ticket.completion_date = datetime.utcnow()
    elif status_update.new_status == "Closed":
        ticket.closed_date = datetime.utcnow()

    if status_update.new_status in ["Completed", "Closed", "Verified"] and ticket.asset_id:
        other_open = db.query(models.Maintenance).filter(
            models.Maintenance.asset_id == ticket.asset_id,
            models.Maintenance.maintenance_id != ticket.maintenance_id,
            models.Maintenance.status.notin_(["Closed", "Verified", "Completed"])
        ).first()
        if not other_open:
            asset = db.query(models.Asset).filter(models.Asset.asset_id == ticket.asset_id).first()
            if asset:
                asset.status = "Active"


    if status_update.new_status in ["Completed", "Closed", "Verified"] and ticket.asset_id:
        other_open = db.query(models.Maintenance).filter(
            models.Maintenance.asset_id == ticket.asset_id,
            models.Maintenance.maintenance_id != ticket.maintenance_id,
            models.Maintenance.status.notin_(["Closed", "Verified", "Completed"])
        ).first()
        if not other_open:
            asset = db.query(models.Asset).filter(models.Asset.asset_id == ticket.asset_id).first()
            if asset:
                asset.status = "Active"


    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)

    create_audit_log(
        db,
        current_user.id,
        "STATUS_CHANGE",
        "maintenance",
        str(ticket_id),
        old_values={"status": old_status},
        new_values={"status": status_update.new_status},
    )
    db.commit()
    return create_api_response(True, "Ticket retrieved", ticket)


# Legacy close endpoint for backward compatibility
@router.put("/{ticket_id}/close", response_model=schemas.APIResponse[schemas.MaintenanceResponse])
def close_maintenance_ticket(
    ticket_id: int,
    remarks: str = "",
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("close_maintenance")),
):
    ticket = (
        db.query(models.Maintenance)
        .filter(models.Maintenance.maintenance_id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Maintenance ticket not found")

    ticket.status = "Closed"
    ticket.closed_date = datetime.utcnow()
    ticket.remarks = remarks
    ticket.updated_at = datetime.utcnow()
    
    if ticket.asset_id:
        other_open = db.query(models.Maintenance).filter(
            models.Maintenance.asset_id == ticket.asset_id,
            models.Maintenance.maintenance_id != ticket.maintenance_id,
            models.Maintenance.status.notin_(["Closed", "Verified", "Completed"])
        ).first()
        if not other_open:
            asset = db.query(models.Asset).filter(models.Asset.asset_id == ticket.asset_id).first()
            if asset:
                asset.status = "Active"

    
    if ticket.asset_id:
        other_open = db.query(models.Maintenance).filter(
            models.Maintenance.asset_id == ticket.asset_id,
            models.Maintenance.maintenance_id != ticket.maintenance_id,
            models.Maintenance.status.notin_(["Closed", "Verified", "Completed"])
        ).first()
        if not other_open:
            asset = db.query(models.Asset).filter(models.Asset.asset_id == ticket.asset_id).first()
            if asset:
                asset.status = "Active"

    db.commit()
    db.refresh(ticket)
    return create_api_response(True, "Ticket retrieved", ticket)


@router.post("/{ticket_id}/photos")
async def upload_maintenance_photos(
    ticket_id: int,
    label: str = "Maintenance Evidence",
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("edit_maintenance")),
):
    ticket = (
        db.query(models.Maintenance)
        .filter(models.Maintenance.maintenance_id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_mimes = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_mimes or ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{ext}' or MIME type '{file.content_type}'")

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    import uuid

    filename = f"maint_{ticket_id}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, "photos", filename)
    with open(save_path, "wb") as f:
        f.write(content)

    attachment = models.Attachment(
        related_id=str(ticket_id),
        related_type="maintenance",
        file_path=f"uploads/photos/{filename}",
        file_type=file.content_type,
        label=label,
        uploaded_by=current_user.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return create_api_response(True, "Photo uploaded", {"attachment_id": attachment.id, "file_path": attachment.file_path, "label": label})


@router.get("/{ticket_id}/photos", response_model=schemas.APIResponse[List[schemas.AttachmentResponse]])
def get_maintenance_photos(
    ticket_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_maintenance")),
):
    photos = db.query(models.Attachment).filter(models.Attachment.related_type == "maintenance", models.Attachment.related_id == str(ticket_id)).all()
    return create_api_response(True, "Photos retrieved", photos)
