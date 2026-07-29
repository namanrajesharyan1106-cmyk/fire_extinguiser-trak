from typing import Any
"""
Dashboard router — live KPIs, trends, department/risk breakdowns.
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, exists
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import database
from ..core import dependencies as auth

router = APIRouter()

def create_api_response(
    success: bool, message: str, data: Any = None, errors: Any = None
) -> dict:
    return create_api_response(True, "Dashboard data retrieved", {"success": success, "message": message, "data": data, "errors": errors})



def _compliance_percent(total: int, compliant: int) -> float:
    if total == 0:
        return 0.0
    return round((compliant / total) * 100, 1)


@router.get("/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    today = datetime.utcnow()
    today_date = today.date()

    total_locations = (
        db.query(models.Location).filter(models.Location.status == "Active").count()
    )
    total_assets = db.query(models.Asset).count()
    installed_assets = (
        db.query(models.Asset)
        .filter(models.Asset.location_id is not None)
        .count()
    )
    unassigned_assets = total_assets - installed_assets

    # Inspections completed today
    inspection_completed_today = (
        db.query(models.Inspection)
        .filter(func.date(models.Inspection.inspection_date) == today_date)
        .count()
    )

    # Inspections due today (locations where next inspection date has passed)
    inspection_due_today = 0
    active_locations = (
        db.query(models.Location)
        .filter(
            models.Location.status == "Active",
            models.Location.inspection_frequency is not None,
        )
        .all()
    )
    for loc in active_locations:
        if loc.last_inspection_date is None:
            inspection_due_today += 1
        else:
            next_due = loc.last_inspection_date + timedelta(
                days=loc.inspection_frequency
            )
            if today >= next_due:
                inspection_due_today += 1

    open_maintenance = (
        db.query(models.Maintenance)
        .filter(models.Maintenance.status.notin_(["Closed", "Verified"]))
        .count()
    )

    # Expired assets
    expired_assets = (
        db.query(models.Asset)
        .filter(
            models.Asset.expiry_date <= today_date,
            models.Asset.status == "Active",
        )
        .count()
    )

    # Refill due
    refill_due = (
        db.query(models.Asset)
        .filter(
            models.Asset.refill_date <= today_date,
            models.Asset.status == "Active",
        )
        .count()
    )

    # Overdue inspections
    overdue_inspections = 0
    for loc in active_locations:
        if loc.last_inspection_date is None:
            overdue_inspections += 1
        else:
            next_due = loc.last_inspection_date + timedelta(
                days=loc.inspection_frequency
            )
            if today > next_due:
                overdue_inspections += 1

    # Locations that have an asset currently assigned
    locations_with_assets = (
        db.query(models.Location)
        .filter(
            models.Location.status == "Active",
            exists().where(
                models.Asset.location_id == models.Location.location_id
            ),
        )
        .count()
    )
    compliance_percent = _compliance_percent(total_locations, locations_with_assets)

    return schemas.DashboardStats(
        total_locations=total_locations,
        total_assets=total_assets,
        installed_assets=installed_assets,
        unassigned_assets=unassigned_assets,
        inspection_due_today=inspection_due_today,
        inspection_completed_today=inspection_completed_today,
        open_maintenance=open_maintenance,
        expired_assets=expired_assets,
        refill_due=refill_due,
        compliance_percent=compliance_percent,
        overdue_inspections=overdue_inspections,
    )


@router.get("/monthly-trend", response_model=List[schemas.MonthlyTrendItem])
def get_monthly_trend(
    months: int = 12,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    result = []
    today = datetime.utcnow()

    for i in range(months - 1, -1, -1):
        target = today.replace(day=1) - timedelta(days=i * 28)
        year = target.year
        month = target.month

        inspections = (
            db.query(models.Inspection)
            .filter(
                extract("year", models.Inspection.inspection_date) == year,
                extract("month", models.Inspection.inspection_date) == month,
            )
            .count()
        )

        passed = (
            db.query(models.Inspection)
            .filter(
                extract("year", models.Inspection.inspection_date) == year,
                extract("month", models.Inspection.inspection_date) == month,
                models.Inspection.overall_status == "Pass",
            )
            .count()
        )

        failed = (
            db.query(models.Inspection)
            .filter(
                extract("year", models.Inspection.inspection_date) == year,
                extract("month", models.Inspection.inspection_date) == month,
                models.Inspection.overall_status == "Fail",
            )
            .count()
        )

        maintenance = (
            db.query(models.Maintenance)
            .filter(
                extract("year", models.Maintenance.opened_date) == year,
                extract("month", models.Maintenance.opened_date) == month,
            )
            .count()
        )

        result.append(
            schemas.MonthlyTrendItem(
                month=target.strftime("%b %Y"),
                inspections=inspections,
                maintenance=maintenance,
                passed=passed,
                failed=failed,
            )
        )

    return result


@router.get("/department-wise", response_model=List[schemas.DepartmentStatsItem])
def get_department_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    departments = db.query(models.Location.department).distinct().all()
    result = []

    for (dept,) in departments:
        if not dept:
            continue
        total = (
            db.query(models.Location)
            .filter(
                models.Location.department == dept,
                models.Location.status == "Active",
            )
            .count()
        )
        installed = (
            db.query(models.Location)
            .filter(
                models.Location.department == dept,
                models.Location.status == "Active",
                exists().where(
                    models.Asset.location_id == models.Location.location_id
                ),
            )
            .count()
        )
        compliance = _compliance_percent(total, installed)

        result.append(
            schemas.DepartmentStatsItem(
                department=dept,
                total_locations=total,
                installed=installed,
                compliance=compliance,
            )
        )

    return result


@router.get("/risk-wise", response_model=List[schemas.RiskStatsItem])
def get_risk_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    from ..core.constants import RISK_CATEGORIES

    result = []
    for category in RISK_CATEGORIES:
        count = (
            db.query(models.Location)
            .filter(
                models.Location.risk_category == category,
                models.Location.status == "Active",
            )
            .count()
        )
        result.append(schemas.RiskStatsItem(risk_category=category, count=count))
    return result


@router.get("/recent-activity")
def get_recent_activity(
    limit: int = 20,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    logs = (
        db.query(models.AuditLog, models.User.name.label("user_name"))
        .outerjoin(models.User, models.AuditLog.user_id == models.User.id)
        .order_by(models.AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    activity = []
    for log, user_name in logs:
        activity.append(
            {
                "id": log.id,
                "action": log.action,
                "table": log.table_name,
                "record_id": log.record_id,
                "user": user_name if user_name else "System",
                "timestamp": log.timestamp.isoformat(),
            }
        )
    return create_api_response(True, "Dashboard data retrieved", {"activity": activity})


@router.get("/plant-wise")
def get_plant_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    plants = db.query(models.Location.plant).distinct().all()
    result = []
    for (plant,) in plants:
        if not plant:
            continue
        total = (
            db.query(models.Location)
            .filter(
                models.Location.plant == plant,
                models.Location.status == "Active",
            )
            .count()
        )
        installed = (
            db.query(models.Location)
            .filter(
                models.Location.plant == plant,
                models.Location.status == "Active",
                exists().where(
                    models.Asset.location_id == models.Location.location_id
                ),
            )
            .count()
        )
        result.append(
            {
                "plant": plant,
                "total_locations": total,
                "installed": installed,
                "compliance": _compliance_percent(total, installed),
            }
        )
    return result


@router.get("/asset-type-distribution")
def get_asset_type_distribution(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    types = (
        db.query(
            models.Asset.asset_type, func.count(models.Asset.asset_id).label("count")
        )
        .group_by(models.Asset.asset_type)
        .all()
    )

    return [{"asset_type": t, "count": c} for t, c in types]
