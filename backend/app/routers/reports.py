"""
Reports router — all report data endpoints scoped by user permissions and plant.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import database
from ..core import dependencies as auth
from ..core.scope import get_user_scope, validate_plant_param
from .auth import create_api_response

router = APIRouter()


@router.get("/asset-register")
def asset_register(
    plant: Optional[str] = None,
    department: Optional[str] = None,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_reports")),
):
    scope = get_user_scope(current_user, db)
    plant = validate_plant_param(plant, scope)

    query = db.query(models.Asset, models.Location).outerjoin(
        models.Location, models.Asset.location_id == models.Location.location_id
    )

    if not scope.is_global:
        if scope.is_empty:
            return create_api_response(True, "Report generated successfully", {"count": 0, "data": []})
        if plant:
            query = query.filter(models.Location.plant == plant)
        else:
            query = query.filter(models.Location.plant.in_(scope.plants))
        if scope.departments:
            query = query.filter(models.Location.department.in_(scope.departments))
    elif plant:
        query = query.filter(models.Location.plant == plant)

    if asset_type:
        query = query.filter(models.Asset.asset_type == asset_type)
    if status:
        query = query.filter(models.Asset.status == status)
    if department:
        query = query.filter(models.Location.department == department)

    results = query.all()
    result = []
    for asset, loc in results:
        result.append(
            {
                "asset_id": asset.asset_id,
                "serial_number": asset.serial_number,
                "asset_type": asset.asset_type,
                "capacity": asset.capacity,
                "manufacturer": asset.manufacturer,
                "manufacturing_date": (
                    asset.manufacturing_date.isoformat()
                    if asset.manufacturing_date
                    else None
                ),
                "refill_date": (
                    asset.refill_date.isoformat() if asset.refill_date else None
                ),
                "expiry_date": (
                    asset.expiry_date.isoformat() if asset.expiry_date else None
                ),
                "amc_due_date": (
                    asset.amc_due_date.isoformat() if asset.amc_due_date else None
                ),
                "status": asset.status,
                "location_id": asset.current_location_id,
                "location_name": loc.location_name if loc else None,
                "plant": loc.plant if loc else None,
                "department": loc.department if loc else None,
                "building": loc.building if loc else None,
                "floor": loc.floor if loc else None,
            }
        )

    return create_api_response(True, "Report generated successfully", {"count": len(result), "data": result})


@router.get("/expired-assets")
def expired_assets_report(
    plant: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_reports")),
):
    scope = get_user_scope(current_user, db)
    plant = validate_plant_param(plant, scope)

    today = datetime.utcnow().date()
    query = (
        db.query(models.Asset, models.Location)
        .join(models.Location, models.Asset.location_id == models.Location.location_id)
        .filter(models.Asset.expiry_date <= today)
    )

    if not scope.is_global:
        if scope.is_empty:
            return create_api_response(True, "Report generated successfully", {"count": 0, "data": []})
        if plant:
            query = query.filter(models.Location.plant == plant)
        else:
            query = query.filter(models.Location.plant.in_(scope.plants))
        if scope.departments:
            query = query.filter(models.Location.department.in_(scope.departments))
    elif plant:
        query = query.filter(models.Location.plant == plant)

    records = query.all()
    result = []
    for asset, loc in records:
        days_expired = (today - asset.expiry_date).days if asset.expiry_date else 0
        result.append(
            {
                "asset_id": asset.asset_id,
                "serial_number": asset.serial_number,
                "asset_type": asset.asset_type,
                "expiry_date": (
                    asset.expiry_date.isoformat() if asset.expiry_date else None
                ),
                "days_expired": days_expired,
                "location": loc.location_name if loc else "Unassigned",
                "department": loc.department if loc else None,
                "plant": loc.plant if loc else None,
            }
        )
    return create_api_response(True, "Report generated successfully", {"count": len(result), "data": result})


@router.get("/refill-due")
def refill_due_report(
    plant: Optional[str] = None,
    days_ahead: int = 30,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_reports")),
):
    scope = get_user_scope(current_user, db)
    plant = validate_plant_param(plant, scope)

    today = datetime.utcnow().date()
    cutoff = today + timedelta(days=days_ahead)
    query = (
        db.query(models.Asset, models.Location)
        .join(models.Location, models.Asset.location_id == models.Location.location_id)
        .filter(
            models.Asset.refill_date <= cutoff,
            models.Asset.status == "Active",
        )
    )

    if not scope.is_global:
        if scope.is_empty:
            return create_api_response(True, "Report generated successfully", {"count": 0, "data": []})
        if plant:
            query = query.filter(models.Location.plant == plant)
        else:
            query = query.filter(models.Location.plant.in_(scope.plants))
        if scope.departments:
            query = query.filter(models.Location.department.in_(scope.departments))
    elif plant:
        query = query.filter(models.Location.plant == plant)

    records = query.all()
    result = []
    for asset, loc in records:
        days_diff = (asset.refill_date - today).days if asset.refill_date else 0
        result.append(
            {
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type,
                "refill_date": (
                    asset.refill_date.isoformat() if asset.refill_date else None
                ),
                "status": "Overdue" if days_diff < 0 else f"Due in {days_diff} days",
                "location": loc.location_name if loc else "Unassigned",
                "department": loc.department if loc else None,
                "plant": loc.plant if loc else None,
            }
        )
    return create_api_response(True, "Report generated successfully", {"count": len(result), "data": result})


@router.get("/inspection-history")
def inspection_history_report(
    plant: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    location_id: Optional[str] = None,
    overall_status: Optional[str] = None,
    limit: int = 500,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_reports")),
):
    scope = get_user_scope(current_user, db)
    plant = validate_plant_param(plant, scope)

    query = db.query(models.Inspection, models.Location).join(
        models.Location, models.Inspection.location_id == models.Location.location_id
    )

    if not scope.is_global:
        if scope.is_empty:
            return create_api_response(True, "Report generated successfully", {"count": 0, "data": []})
        if plant:
            query = query.filter(models.Location.plant == plant)
        else:
            query = query.filter(models.Location.plant.in_(scope.plants))
        if scope.departments:
            query = query.filter(models.Location.department.in_(scope.departments))
    elif plant:
        query = query.filter(models.Location.plant == plant)

    if start_date:
        query = query.filter(
            models.Inspection.inspection_date
            >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date:
        query = query.filter(
            models.Inspection.inspection_date
            <= datetime.combine(end_date, datetime.max.time())
        )
    if location_id:
        query = query.filter(models.Inspection.location_id == location_id)
    if overall_status:
        query = query.filter(models.Inspection.overall_status == overall_status)

    inspections = (
        query.order_by(models.Inspection.inspection_date.desc()).limit(limit).all()
    )
    result = []
    for insp, loc in inspections:
        result.append(
            {
                "inspection_id": insp.inspection_id,
                "location_id": insp.location_id,
                "location_name": loc.location_name if loc else None,
                "department": loc.department if loc else None,
                "plant": loc.plant if loc else None,
                "asset_id": insp.asset_id,
                "inspector": insp.inspector,
                "date": insp.inspection_date.isoformat() if insp.inspection_date else None,
                "overall_status": insp.overall_status,
                "pressure": insp.pressure,
                "seal": insp.seal,
                "pin": insp.pin,
                "gauge": insp.gauge,
                "hose": insp.hose,
                "nozzle": insp.nozzle,
                "remarks": insp.remarks,
            }
        )
    return create_api_response(True, "Report generated successfully", {"count": len(result), "data": result})


@router.get("/maintenance-pending")
def maintenance_pending_report(
    plant: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_reports")),
):
    scope = get_user_scope(current_user, db)
    plant = validate_plant_param(plant, scope)

    query = (
        db.query(models.Maintenance, models.Location)
        .join(models.Location, models.Maintenance.location_id == models.Location.location_id)
        .filter(models.Maintenance.status.notin_(["Closed", "Verified"]))
    )

    if not scope.is_global:
        if scope.is_empty:
            return create_api_response(True, "Report generated successfully", {"count": 0, "data": []})
        if plant:
            query = query.filter(models.Location.plant == plant)
        else:
            query = query.filter(models.Location.plant.in_(scope.plants))
        if scope.departments:
            query = query.filter(models.Location.department.in_(scope.departments))
    elif plant:
        query = query.filter(models.Location.plant == plant)

    tickets = query.order_by(models.Maintenance.opened_date.desc()).all()
    result = []
    for t, loc in tickets:
        days_open = (datetime.utcnow() - t.opened_date).days if t.opened_date else 0
        result.append(
            {
                "maintenance_id": t.maintenance_id,
                "asset_id": t.asset_id,
                "location": loc.location_name if loc else None,
                "plant": loc.plant if loc else None,
                "issue": t.issue,
                "priority": t.priority,
                "status": t.status,
                "assigned_to": t.assigned_to,
                "opened_date": t.opened_date.isoformat() if t.opened_date else None,
                "days_open": days_open,
            }
        )
    return create_api_response(True, "Report generated successfully", {"count": len(result), "data": result})


@router.get("/maintenance-closed")
def maintenance_closed_report(
    plant: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 500,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_reports")),
):
    scope = get_user_scope(current_user, db)
    plant = validate_plant_param(plant, scope)

    query = (
        db.query(models.Maintenance, models.Location)
        .join(models.Location, models.Maintenance.location_id == models.Location.location_id)
        .filter(models.Maintenance.status.in_(["Closed", "Verified"]))
    )

    if not scope.is_global:
        if scope.is_empty:
            return create_api_response(True, "Report generated successfully", {"count": 0, "data": []})
        if plant:
            query = query.filter(models.Location.plant == plant)
        else:
            query = query.filter(models.Location.plant.in_(scope.plants))
        if scope.departments:
            query = query.filter(models.Location.department.in_(scope.departments))
    elif plant:
        query = query.filter(models.Location.plant == plant)

    if start_date:
        query = query.filter(
            models.Maintenance.closed_date
            >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date:
        query = query.filter(
            models.Maintenance.closed_date
            <= datetime.combine(end_date, datetime.max.time())
        )

    tickets = query.order_by(models.Maintenance.closed_date.desc()).limit(limit).all()
    result = []
    for t, loc in tickets:
        duration = None
        if t.closed_date:
            duration = (t.closed_date - t.opened_date).days if t.opened_date else 0
        result.append(
            {
                "maintenance_id": t.maintenance_id,
                "asset_id": t.asset_id,
                "location": loc.location_name if loc else None,
                "plant": loc.plant if loc else None,
                "issue": t.issue,
                "priority": t.priority,
                "status": t.status,
                "opened_date": t.opened_date.isoformat() if t.opened_date else None,
                "closed_date": t.closed_date.isoformat() if t.closed_date else None,
                "duration_days": duration,
                "verified_by": t.verified_by,
            }
        )
    return create_api_response(True, "Report generated successfully", {"count": len(result), "data": result})


@router.get("/compliance")
def compliance_report(
    plant: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_reports")),
):
    """Compliance summary by plant and department."""
    scope = get_user_scope(current_user, db)
    plant = validate_plant_param(plant, scope)

    loc_query = db.query(models.Location.department, models.Location.plant).distinct()
    if not scope.is_global:
        if scope.is_empty:
            return create_api_response(True, "Report generated successfully", {"count": 0, "data": []})
        if plant:
            loc_query = loc_query.filter(models.Location.plant == plant)
        else:
            loc_query = loc_query.filter(models.Location.plant.in_(scope.plants))
        if scope.departments:
            loc_query = loc_query.filter(models.Location.department.in_(scope.departments))
    elif plant:
        loc_query = loc_query.filter(models.Location.plant == plant)

    departments = loc_query.all()
    result = []
    for dept, p_name in departments:
        if not dept:
            continue
        total = (
            db.query(models.Location)
            .filter(
                models.Location.department == dept,
                models.Location.plant == p_name,
                models.Location.status == "Active",
            )
            .count()
        )
        installed = (
            db.query(models.Location)
            .join(models.Asset, models.Asset.location_id == models.Location.location_id)
            .filter(
                models.Location.department == dept,
                models.Location.plant == p_name,
            )
            .count()
        )
        compliance = round((installed / total) * 100, 1) if total > 0 else 0.0
        result.append(
            {
                "plant": p_name,
                "department": dept,
                "total_locations": total,
                "installed": installed,
                "uninstalled": total - installed,
                "compliance_percent": compliance,
            }
        )
    return create_api_response(True, "Report generated successfully", {"count": len(result), "data": result})


@router.get("/asset-movement")
def asset_movement_report(
    plant: Optional[str] = None,
    asset_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 500,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_reports")),
):
    scope = get_user_scope(current_user, db)
    plant = validate_plant_param(plant, scope)

    query = db.query(models.AssetHistory)
    if not scope.is_global:
        if scope.is_empty:
            return {"count": 0, "data": []}
        # Filter movements where asset's current or target location is in user's plants
        if plant:
            query = query.join(models.Asset, models.AssetHistory.asset_id == models.Asset.asset_id).join(
                models.Location, models.Asset.location_id == models.Location.location_id
            ).filter(models.Location.plant == plant)
        else:
            query = query.join(models.Asset, models.AssetHistory.asset_id == models.Asset.asset_id).join(
                models.Location, models.Asset.location_id == models.Location.location_id
            ).filter(models.Location.plant.in_(scope.plants))
    elif plant:
        query = query.join(models.Asset, models.AssetHistory.asset_id == models.Asset.asset_id).join(
            models.Location, models.Asset.location_id == models.Location.location_id
        ).filter(models.Location.plant == plant)

    if asset_id:
        query = query.filter(models.AssetHistory.asset_id == asset_id)
    if start_date:
        query = query.filter(
            models.AssetHistory.movement_date
            >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date:
        query = query.filter(
            models.AssetHistory.movement_date
            <= datetime.combine(end_date, datetime.max.time())
        )

    records = (
        query.order_by(models.AssetHistory.movement_date.desc()).limit(limit).all()
    )
    return {
        "count": len(records),
        "data": [schemas.AssetHistoryResponse.model_validate(r) for r in records],
    }
