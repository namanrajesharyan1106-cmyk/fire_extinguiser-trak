from typing import List, Optional, Tuple
import datetime

from sqlalchemy.orm import Session

from ..models.asset import Asset, AssetHistory
from ..models.maintenance import Maintenance
from ..repositories.asset_repository import asset_repo
from ..repositories.location_repository import location_repo
from ..utils.asset_checks import is_asset_expired, is_refill_overdue


def validate_asset_assignment(
    db: Session, asset_id: str, location_id: str, force: bool = False
) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    asset = asset_repo.get(db, asset_id)
    location = location_repo.get(db, location_id)

    print("\n" + "="*50)
    print("STEP 2: ASSET LOOKUP")
    print(f"Asset Exists: {asset is not None}")
    if asset:
        print(f"Asset Active: {asset.status == 'Active'}")
        print(f"Current Location: {asset.location_id}")
        print(f"Asset Type: {asset.asset_type}")
        print(f"Capacity: {asset.capacity}")
        print(f"Complete Asset Object: {asset.__dict__}")

    print("\nSTEP 3: LOCATION LOOKUP")
    print(f"Location Exists: {location is not None}")
    if location:
        print(f"Location Active: {location.status == 'Active'}")
        print(f"Location ID: {location.location_id}")
        print(f"Location Name: {location.location_name}")
        print(f"Required Asset: {location.required_asset_type}")
        print(f"Capacity: {location.required_capacity}")
        print(f"Current Assigned Assets: {location.current_assets_count}")
        print(f"Remaining Capacity: {location.remaining_capacity}")
        print(f"Complete Location Object: {location.__dict__}")
    print("="*50 + "\n")

    if not asset:
        return False, [f"Asset '{asset_id}' not found."], []
    if not location:
        return False, [f"Location '{location_id}' not found."], []

    # 1. Asset already assigned to a different location
    if asset.location_id and asset.location_id != location_id:
        warnings.append(
            f"This asset is currently assigned to Location {asset.location_id} and will be moved to Location {location_id}."
        )

    # 2. Asset is expired
    if is_asset_expired(asset):
        errors.append(f"Asset '{asset_id}' has expired. Cannot be assigned.")

    # 3. Asset is under maintenance
    open_ticket = (
        db.query(Maintenance)
        .filter(
            Maintenance.asset_id == asset_id,
            Maintenance.status.notin_(["Closed", "Verified"]),
        )
        .first()
    )
    if open_ticket:
        errors.append(
            f"Asset '{asset_id}' has an open maintenance ticket. Close before assigning."
        )

    # 4. Type mismatch
    if (
        location.required_asset_type
        and asset.asset_type
        and location.required_asset_type.lower() != asset.asset_type.lower()
    ):
        errors.append(
            f"Type mismatch: Location requires '{location.required_asset_type}' but asset is '{asset.asset_type}'."
        )

    # 5. Capacity mismatch
    if (
        location.required_capacity
        and asset.capacity
        and location.required_capacity.lower() != asset.capacity.lower()
    ):
        errors.append("Capacity mismatch.")

    # Warnings
    if is_refill_overdue(asset):
        warnings.append(f"Asset '{asset_id}' refill is overdue.")

    # 7. Check Capacity & Existing Occupant
    existing_occupant = db.query(Asset).filter(Asset.location_id == location_id, Asset.asset_id != asset_id).first()
    if existing_occupant:
        warnings.append(
            f"Location '{location_id}' currently holds asset '{existing_occupant.asset_id}'. Reassignment will replace it."
        )
    elif location.current_assets_count >= location.max_assets:
        if not (asset.location_id == location_id):  # if it's not already in this location
            errors.append(f"Location '{location_id}' is at full capacity ({location.max_assets}).")

    if (errors or warnings) and not force:
        print(f"STEP 4: MASTER DATA VALIDATION FAILED - Errors: {errors}")
        return False, errors, warnings

    print("STEP 4: MASTER DATA VALIDATION PASSED")
    return True, errors, warnings


def perform_asset_assignment(
    db: Session,
    asset_id: str,
    location_id: str,
    changed_by: str,
    movement_type: str = "Assigned",
    movement_reason: str = "Assigned to location",
    comments: Optional[str] = None,
) -> dict:
    with db.begin_nested():
        asset = db.query(Asset).filter(Asset.asset_id == asset_id).with_for_update().first()
        if not asset:
            raise ValueError(f"Asset '{asset_id}' not found.")
        location = location_repo.get(db, location_id)

        old_location_id = asset.location_id

        # If another asset is currently occupying this location, safely unlink it to respect UNIQUE(location_id)
        existing_occupant = db.query(Asset).filter(Asset.location_id == location_id, Asset.asset_id != asset_id).first()
        if existing_occupant:
            existing_occupant.location_id = None
            db.add(existing_occupant)
            db.add(AssetHistory(
                asset_id=existing_occupant.asset_id,
                old_location_id=location_id,
                new_location_id=None,
                movement_type="Transfer",
                movement_reason=f"Replaced by {asset_id} at {location_id}",
                changed_by=changed_by,
                movement_date=datetime.datetime.utcnow(),
            ))
            db.flush()

        # Assign
        asset.location_id = location_id

        # History record
        history = AssetHistory(
            asset_id=asset_id,
            old_location_id=old_location_id,
            new_location_id=location_id,
            movement_type=movement_type,
            movement_reason=movement_reason,
            changed_by=changed_by,
            comments=comments,
            movement_date=datetime.datetime.utcnow(),
        )

        db.add(asset)
        db.add(history)
    
    print("\n" + "="*50)
    print("STEP 6: DATABASE UPDATE")
    print("Immediately before db.commit()")
    print(f"Asset Object: {asset.__dict__}")
    print(f"Location Object: {location.__dict__}")
    print(f"Foreign Key asset.location_id: {asset.location_id}")
    print(f"Location.current_assets_count: {location.current_assets_count}")
    print(f"Generated History ID: {history.id}")
    print("="*50 + "\n")

    db.commit()

    return {
        "message": f"Asset '{asset_id}' successfully assigned to location '{location_id}'.",
        "history_id": history.id,
    }


def unlink_asset_from_location(
    db: Session,
    asset_id: str,
    changed_by: str,
    reason: str = "Manually unlinked",
    movement_type: str = "Transfer",
) -> dict:
    asset = asset_repo.get(db, asset_id)
    if not asset:
        return {"error": f"Asset '{asset_id}' not found."}
    if asset.location_id == False:
        return {"error": f"Asset '{asset_id}' is not assigned to any location."}

    old_location_id = asset.location_id
    asset.location_id = None

    history = AssetHistory(
        asset_id=asset_id,
        old_location_id=old_location_id,
        new_location_id=None,
        movement_type=movement_type,
        movement_reason=reason,
        changed_by=changed_by,
    )

    db.add(asset)
    db.add(history)
    db.commit()

    return {
        "message": f"Asset '{asset_id}' unlinked from location '{old_location_id}'."
    }
