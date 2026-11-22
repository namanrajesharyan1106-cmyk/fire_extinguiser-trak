"""
Secure File Serving Router — Authenticated, Scoped, Hardened Headers.
"""

import os
import mimetypes
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import models
from ..core import database
from ..core import dependencies as auth
from ..core.config import settings
from ..core.scope import check_record_scope

router = APIRouter()

ALLOWED_KINDS = {"photos", "qr"}


@router.get("/{kind}/{filename}")
def serve_file(
    kind: str,
    filename: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Serve uploaded files with:
    - Authentication required (current_user)
    - Plant/department scope checks on owning record
    - Path traversal protection
    - Security headers: X-Content-Type-Options, Content-Disposition, Cache-Control
    """
    if kind not in ALLOWED_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file category '{kind}'. Allowed: {list(ALLOWED_KINDS)}",
        )

    # Path traversal protection
    safe_filename = os.path.basename(filename)
    if safe_filename != filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename format",
        )

    dir_path = os.path.join(settings.UPLOAD_DIR, kind)
    file_path = os.path.join(dir_path, safe_filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Scope verification on the owning record
    if current_user.role != "ADMIN":
        record_found = False

        if kind == "photos":
            # 1. Check Attachment (inspection or maintenance)
            attachment = (
                db.query(models.Attachment)
                .filter(models.Attachment.file_path.like(f"%{safe_filename}"))
                .first()
            )
            if attachment:
                record_found = True
                if attachment.related_type == "inspection":
                    try:
                        insp_id = int(attachment.related_id)
                        insp = db.query(models.Inspection).filter(models.Inspection.inspection_id == insp_id).first()
                        if not insp or not check_record_scope(insp, current_user, db):
                            raise HTTPException(status_code=404, detail="File not found")
                    except ValueError:
                        raise HTTPException(status_code=404, detail="File not found")
                elif attachment.related_type == "maintenance":
                    try:
                        maint_id = int(attachment.related_id)
                        maint = db.query(models.Maintenance).filter(models.Maintenance.maintenance_id == maint_id).first()
                        if not maint or not check_record_scope(maint, current_user, db):
                            raise HTTPException(status_code=404, detail="File not found")
                        # Technician check
                        if current_user.role == "MAINTENANCE" and maint.technician_id is not None and maint.technician_id != current_user.id:
                            raise HTTPException(status_code=404, detail="File not found")
                    except ValueError:
                        raise HTTPException(status_code=404, detail="File not found")

            # 2. Check Asset.photo
            if not record_found:
                asset = (
                    db.query(models.Asset)
                    .filter(models.Asset.photo.like(f"%{safe_filename}"))
                    .first()
                )
                if asset:
                    record_found = True
                    if not check_record_scope(asset, current_user, db):
                        raise HTTPException(status_code=404, detail="File not found")

            if not record_found:
                # File exists on disk but is not linked to any scoped record
                raise HTTPException(status_code=404, detail="File not found")

        elif kind == "qr":
            # 1. Check Location.qr_image_path
            loc = (
                db.query(models.Location)
                .filter(models.Location.qr_image_path.like(f"%{safe_filename}"))
                .first()
            )
            if loc:
                record_found = True
                if not check_record_scope(loc, current_user, db):
                    raise HTTPException(status_code=404, detail="File not found")

            # 2. Check Asset barcode / QR
            if not record_found:
                # Strip extension to check against asset barcode/ID
                name_no_ext = os.path.splitext(safe_filename)[0]
                asset = (
                    db.query(models.Asset)
                    .filter((models.Asset.barcode == name_no_ext) | (models.Asset.asset_id == name_no_ext))
                    .first()
                )
                if asset:
                    record_found = True
                    if not check_record_scope(asset, current_user, db):
                        raise HTTPException(status_code=404, detail="File not found")

            if not record_found:
                raise HTTPException(status_code=404, detail="File not found")

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        ext = os.path.splitext(safe_filename)[1].lower()
        ext_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime_type = ext_map.get(ext, "application/octet-stream")

    is_image = mime_type.startswith("image/")
    disposition = f'inline; filename="{safe_filename}"' if is_image else f'attachment; filename="{safe_filename}"'

    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-cache",
        "Content-Disposition": disposition,
    }

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        headers=headers,
    )
