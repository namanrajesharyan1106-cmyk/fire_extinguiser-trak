"""
Notification Service — event-driven notification creation for expiry/due checks.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..utils import create_notifications_for_roles


def check_asset_expiry_notifications(db: Session):
    """Check for assets approaching expiry and create notifications."""
    today = datetime.utcnow().date()
    alert_date = today + timedelta(days=settings.EXPIRY_ALERT_DAYS)

    # Expired
    expired = (
        db.query(models.Asset)
        .filter(
            models.Asset.expiry_date <= today,
            models.Asset.status == "Active",
        )
        .all()
    )
    for asset in expired:
        create_notifications_for_roles(
            db,
            roles=["ADMIN", "SAFETY HEAD", "SAFETY OFFICER"],
            notif_type="ASSET_EXPIRED",
            message=f"Asset '{asset.asset_id}' ({asset.asset_type}) has expired on {asset.expiry_date}.",
            related_id=asset.asset_id,
            related_type="asset",
        )

    # Approaching expiry
    approaching = (
        db.query(models.Asset)
        .filter(
            models.Asset.expiry_date > today,
            models.Asset.expiry_date <= alert_date,
            models.Asset.status == "Active",
        )
        .all()
    )
    for asset in approaching:
        days_left = (asset.expiry_date - today).days if asset.expiry_date else 0
        create_notifications_for_roles(
            db,
            roles=["SAFETY HEAD", "SAFETY OFFICER"],
            notif_type="ASSET_EXPIRED",
            message=f"Asset '{asset.asset_id}' expires in {days_left} day(s) ({asset.expiry_date}).",
            related_id=asset.asset_id,
            related_type="asset",
        )

    db.commit()


def check_refill_notifications(db: Session):
    """Check for assets with overdue or upcoming refills."""
    today = datetime.utcnow().date()
    alert_date = today + timedelta(days=settings.REFILL_ALERT_DAYS)

    overdue = (
        db.query(models.Asset)
        .filter(
            models.Asset.refill_date <= today,
            models.Asset.status == "Active",
        )
        .all()
    )
    for asset in overdue:
        create_notifications_for_roles(
            db,
            roles=["SAFETY HEAD", "SAFETY OFFICER", "MAINTENANCE"],
            notif_type="REFILL_DUE",
            message=f"Asset '{asset.asset_id}' refill is overdue (last refill: {asset.refill_date}).",
            related_id=asset.asset_id,
            related_type="asset",
        )

    upcoming = (
        db.query(models.Asset)
        .filter(
            models.Asset.refill_date > today,
            models.Asset.refill_date <= alert_date,
            models.Asset.status == "Active",
        )
        .all()
    )
    for asset in upcoming:
        days_left = (asset.refill_date - today).days if asset.refill_date else 0
        create_notifications_for_roles(
            db,
            roles=["SAFETY OFFICER", "MAINTENANCE"],
            notif_type="REFILL_DUE",
            message=f"Asset '{asset.asset_id}' refill due in {days_left} day(s).",
            related_id=asset.asset_id,
            related_type="asset",
        )

    db.commit()


def check_amc_notifications(db: Session):
    """Check for AMC due alerts."""
    today = datetime.utcnow().date()
    alert_date = today + timedelta(days=settings.AMC_ALERT_DAYS)

    due_assets = (
        db.query(models.Asset)
        .filter(
            models.Asset.amc_due_date.is_not(None),
            models.Asset.amc_due_date <= alert_date,
            models.Asset.status == "Active",
        )
        .all()
    )
    for asset in due_assets:
        days_left = (
            (asset.amc_due_date - today).days if (asset.amc_due_date and asset.amc_due_date > today) else 0
        )
        msg = (
            f"AMC for asset '{asset.asset_id}' is overdue."
            if days_left <= 0
            else f"AMC for asset '{asset.asset_id}' due in {days_left} day(s)."
        )
        create_notifications_for_roles(
            db,
            roles=["ADMIN", "SAFETY HEAD"],
            notif_type="AMC_DUE",
            message=msg,
            related_id=asset.asset_id,
            related_type="asset",
        )
    db.commit()


def check_inspection_overdue_notifications(db: Session):
    """Check for locations with overdue inspections."""
    locations = (
        db.query(models.Location)
        .filter(
            models.Location.status == "Active",
            models.Location.inspection_frequency.is_not(None),
        )
        .all()
    )

    for loc in locations:
        if loc.last_inspection_date is None:
            continue
        next_due = loc.last_inspection_date + timedelta(days=loc.inspection_frequency or 0)
        if datetime.utcnow() > next_due:
            days_overdue = (datetime.utcnow() - next_due).days
            create_notifications_for_roles(
                db,
                roles=["SAFETY HEAD", "SAFETY OFFICER"],
                notif_type="INSPECTION_OVERDUE",
                message=(
                    f"Location '{loc.location_id}' ({loc.location_name}) "
                    f"inspection overdue by {days_overdue} day(s)."
                ),
                related_id=loc.location_id,
                related_type="location",
            )
    db.commit()
