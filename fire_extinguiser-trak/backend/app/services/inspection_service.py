"""
Inspection Service — auto-status calculation and maintenance ticket creation.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from .. import models
from ..constants import MANDATORY_CHECKLIST_FIELDS
from ..utils import create_notifications_for_roles


def process_inspection(
    db: Session,
    inspection: models.Inspection,
    current_user: models.User,
) -> models.Inspection:
    """
    Post-save inspection processing:
    1. Auto-calculate overall status (already done before save)
    2. If FAIL → create maintenance ticket
    3. Create notifications
    4. Update location's last_inspection_date
    """
    # Update location's last inspection date
    location = (
        db.query(models.Location)
        .filter(models.Location.location_id == inspection.location_id)
        .first()
    )
    if location:
        location.last_inspection_date = datetime.utcnow()
        db.add(location)

    # Auto-create maintenance ticket on FAIL
    if inspection.overall_status == "Fail":
        failed_fields = []
        for field in MANDATORY_CHECKLIST_FIELDS:
            val = getattr(inspection, field, None)
            if val and val.lower() == "fail":
                failed_fields.append(field.replace("_", " ").title())

        issue_text = (
            f"Inspection #{inspection.inspection_id} FAILED. "
            f"Failed checks: {', '.join(failed_fields) if failed_fields else 'see remarks'}. "
            f"Remarks: {inspection.remarks or 'N/A'}"
        )

        ticket = models.Maintenance(
            asset_id=inspection.asset_id,
            location_id=inspection.location_id,
            issue=issue_text,
            priority="High",
            status="Open",
            inspection_id=inspection.inspection_id,
            remarks="Auto-generated from failed inspection",
            opened_date=datetime.utcnow(),
        )
        db.add(ticket)
        db.flush()  # Get ticket ID

        asset = db.query(models.Asset).filter(models.Asset.asset_id == inspection.asset_id).first()
        if asset:
            asset.status = "Under Maintenance"

        # Notify Safety Officers + Maintenance team
        create_notifications_for_roles(
            db,
            roles=["ADMIN", "SAFETY HEAD", "SAFETY OFFICER", "MAINTENANCE"],
            notif_type="INSPECTION_FAILED",
            message=(
                f"Inspection FAILED at location '{inspection.location_id}'. "
                f"Maintenance ticket #{ticket.maintenance_id} auto-created."
            ),
            related_id=str(inspection.inspection_id),
            related_type="inspection",
        )

    elif inspection.overall_status == "Conditional Pass":
        create_notifications_for_roles(
            db,
            roles=["SAFETY HEAD", "SAFETY OFFICER"],
            notif_type="INSPECTION_FAILED",
            message=(
                f"Inspection at location '{inspection.location_id}' has Conditional Pass. "
                f"Please review inspection #{inspection.inspection_id}."
            ),
            related_id=str(inspection.inspection_id),
            related_type="inspection",
        )

    db.commit()
    db.refresh(inspection)
    return inspection
