import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import qrcode
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.constants import ALL_CHECKLIST_FIELDS, MANDATORY_CHECKLIST_FIELDS

# =============================================================================
# Upload Directories
# =============================================================================

UPLOAD_DIR = settings.UPLOAD_DIR

Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(os.path.join(UPLOAD_DIR, "qr")).mkdir(parents=True, exist_ok=True)
Path(os.path.join(UPLOAD_DIR, "photos")).mkdir(parents=True, exist_ok=True)

# =============================================================================
# QR Code Generation
# =============================================================================


def generate_qr_code_image(data: str, location_id: str) -> str:
    """
    Generate QR code image for a location.
    Returns relative file path.
    """

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(UPLOAD_DIR, "qr", filename)

    with open(filepath, "wb") as f:
        img.save(f)

    return f"uploads/qr/{filename}"


# =============================================================================
# Inspection Status
# =============================================================================


def auto_calculate_inspection_status(checklist: dict) -> str:
    """
    Calculate inspection result based on checklist.
    """

    mandatory_fail = any(
        str(checklist.get(field, "")).lower() == "fail"
        for field in MANDATORY_CHECKLIST_FIELDS
    )

    if mandatory_fail:
        return "Fail"

    optional_fail = any(
        str(checklist.get(field, "")).lower() == "fail"
        for field in ALL_CHECKLIST_FIELDS
        if field not in MANDATORY_CHECKLIST_FIELDS
    )

    if optional_fail:
        return "Conditional Pass"

    return "Pass"


# =============================================================================
# Audit Logs
# =============================================================================


def create_audit_log(
    db: Session,
    user_id: int,
    action: str,
    table_name: str,
    record_id: str,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    """
    Create audit log entry.
    """

    from ..models import AuditLog

    log = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=str(record_id),
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        ip_address=ip_address,
        timestamp=datetime.utcnow(),
    )

    db.add(log)


# =============================================================================
# Notifications
# =============================================================================


def create_notification(
    db: Session,
    user_id: int,
    notif_type: str,
    message: str,
    related_id: Optional[str] = None,
    related_type: Optional[str] = None,
):
    """
    Create notification.
    """

    from ..models import Notification

    notification = Notification(
        user_id=user_id,
        type=notif_type,
        message=message,
        related_id=str(related_id) if related_id else None,
        related_type=related_type,
        is_read=False,
        created_at=datetime.utcnow(),
    )

    db.add(notification)


def create_notifications_for_roles(
    db: Session,
    roles: list,
    notif_type: str,
    message: str,
    related_id: Optional[str] = None,
    related_type: Optional[str] = None,
):
    """
    Create notification for all active users of given roles.
    """

    from ..models import User

    users = (
        db.query(User)
        .filter(
            User.role.in_(roles),
            User.status == "Active",
        )
        .all()
    )

    for user in users:
        create_notification(
            db=db,
            user_id=user.id,
            notif_type=notif_type,
            message=message,
            related_id=related_id,
            related_type=related_type,
        )


# =============================================================================
# Asset Checks
# =============================================================================


def is_asset_expired(asset) -> bool:
    """
    Check whether extinguisher has expired.
    """

    if asset.expiry_date == False:
        return False

    return asset.expiry_date < datetime.utcnow().date()


def is_refill_overdue(asset) -> bool:
    """
    Check refill due date.
    """

    if asset.refill_date == False:
        return False

    return asset.refill_date < datetime.utcnow().date()


# =============================================================================
# Model Serializer
# =============================================================================


def model_to_dict(obj, exclude=None):
    """
    Convert SQLAlchemy model into dictionary.
    """

    if exclude is None:
        exclude = ["password_hash"]

    result = {}

    for column in obj.__table__.columns:
        if column.name in exclude:
            continue

        value = getattr(obj, column.name)

        if hasattr(value, "isoformat"):
            value = value.isoformat()

        result[column.name] = value

    return result


# =============================================================================
# Image Validation & Sanitization
# =============================================================================


async def validate_and_sanitize_image(
    file,
    max_size_mb: int = settings.MAX_UPLOAD_SIZE_MB,
) -> tuple[bytes, str, str]:
    """
    Stream and validate image content.
    - Enforces size limit by reading in chunks.
    - Validates real image content with Pillow (verify).
    - Strips EXIF metadata and normalizes orientation.
    - Re-encodes to safe format (JPEG, PNG, WEBP).
    Returns (sanitized_bytes, file_extension, mime_type).
    """
    from PIL import Image, ImageOps
    import io
    from fastapi import HTTPException

    chunk_size = 64 * 1024  # 64KB
    max_bytes = max_size_mb * 1024 * 1024
    total_bytes = 0
    buffer = io.BytesIO()

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds maximum allowed size of {max_size_mb}MB",
            )
        buffer.write(chunk)

    if total_bytes == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    raw_bytes = buffer.getvalue()

    # Step 1: Pillow verify
    try:
        verify_img = Image.open(io.BytesIO(raw_bytes))
        verify_img.verify()
        detected_format = verify_img.format
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file or corrupt image data",
        )

    if not detected_format or detected_format.upper() not in ["JPEG", "PNG", "WEBP"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format '{detected_format}'. Allowed: JPEG, PNG, WEBP",
        )

    # Step 2: Re-open image to strip EXIF and re-encode
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img = ImageOps.exif_transpose(img)

        output_format = detected_format.upper()
        ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
        mime_map = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

        if output_format == "JPEG" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        out_buffer = io.BytesIO()
        img.save(out_buffer, format=output_format)
        sanitized_bytes = out_buffer.getvalue()

        return sanitized_bytes, ext_map[output_format], mime_map[output_format]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process and sanitize image: {str(e)}",
        )

