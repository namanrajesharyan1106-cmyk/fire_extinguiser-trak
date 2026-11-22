"""
Dashboard router — live KPIs, trends, department/risk breakdowns.
"""

from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, exists
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import database
from ..core import dependencies as auth
from ..core.scope import apply_scope

router = APIRouter()

def create_api_response(
    success: bool, message: str, data: Any = None, errors: Any = None
) -> dict:
    return {"success": success, "message": message, "data": data, "errors": errors}



def _compliance_percent(total: int, compliant: int) -> float:
    if total == 0:
        return 0.0
    return round((compliant / total) * 100, 1)


@router.get("/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    today = datetime.utcnow()
    today_date = today.date()

    # Parse optional filter dates
    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None
    as_of_date = today_date

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            as_of_date = end_dt.date()
        except ValueError:
            pass

    # Scoped base queries
    scoped_locations = apply_scope(db.query(models.Location), current_user, db, models.Location)
    scoped_assets = apply_scope(db.query(models.Asset), current_user, db, models.Asset)

    # Master inventory counts — preserved as master totals per requirements (scoped by plant)
    total_locations = scoped_locations.filter(models.Location.status == "Active").count()
    total_assets = scoped_assets.count()
    installed_assets = scoped_assets.filter(models.Asset.location_id.is_not(None)).count()
    unassigned_assets = total_assets - installed_assets

    # Inspections count: if date range provided, count within range; otherwise count completed today
    inspections_in_range = None
    inspections_passed = None
    inspections_failed = None

    base_insp = apply_scope(db.query(models.Inspection), current_user, db, models.Inspection)

    if start_dt and end_dt:
        insp_query = base_insp.filter(
            models.Inspection.inspection_date >= start_dt,
            models.Inspection.inspection_date <= end_dt,
        )
        inspections_in_range = insp_query.count()
        inspection_completed_today = inspections_in_range
        inspections_passed = insp_query.filter(models.Inspection.overall_status == "Pass").count()
        inspections_failed = insp_query.filter(models.Inspection.overall_status == "Fail").count()
    elif start_dt:
        insp_query = base_insp.filter(
            models.Inspection.inspection_date >= start_dt
        )
        inspections_in_range = insp_query.count()
        inspection_completed_today = inspections_in_range
        inspections_passed = insp_query.filter(models.Inspection.overall_status == "Pass").count()
        inspections_failed = insp_query.filter(models.Inspection.overall_status == "Fail").count()
    elif end_dt:
        insp_query = base_insp.filter(
            models.Inspection.inspection_date <= end_dt
        )
        inspections_in_range = insp_query.count()
        inspection_completed_today = inspections_in_range
        inspections_passed = insp_query.filter(models.Inspection.overall_status == "Pass").count()
        inspections_failed = insp_query.filter(models.Inspection.overall_status == "Fail").count()
    else:
        inspection_completed_today = (
            base_insp
            .filter(func.date(models.Inspection.inspection_date) == today_date)
            .count()
        )

    # Maintenance in range
    base_maint = apply_scope(db.query(models.Maintenance), current_user, db, models.Maintenance)
    maintenance_in_range = None
    if start_dt and end_dt:
        maintenance_in_range = (
            base_maint
            .filter(
                models.Maintenance.opened_date >= start_dt,
                models.Maintenance.opened_date <= end_dt,
            )
            .count()
        )

    # Inspections due (locations where next inspection date has passed as of target date)
    inspection_due_today = 0
    overdue_inspections = 0
    active_locations = (
        scoped_locations
        .filter(
            models.Location.status == "Active",
            models.Location.inspection_frequency.is_not(None),
        )
        .all()
    )
    for loc in active_locations:
        if loc.last_inspection_date is None:
            inspection_due_today += 1
            overdue_inspections += 1
        else:
            next_due = loc.last_inspection_date + timedelta(
                days=loc.inspection_frequency
            )
            if as_of_date >= next_due.date():
                inspection_due_today += 1
            if as_of_date > next_due.date():
                overdue_inspections += 1

    # Open maintenance tickets (not closed or verified; if end_date given, opened on or before end_date)
    open_maint_query = base_maint.filter(
        models.Maintenance.status.notin_(["Closed", "Verified"])
    )
    if end_dt:
        open_maint_query = open_maint_query.filter(
            (models.Maintenance.opened_date <= end_dt) | (models.Maintenance.opened_date.is_(None))
        )
    open_maintenance = open_maint_query.count()

    # Expired assets as of target date
    expired_assets = (
        scoped_assets
        .filter(
            models.Asset.expiry_date <= as_of_date,
            models.Asset.status == "Active",
        )
        .count()
    )

    # Refill due as of target date
    refill_due = (
        scoped_assets
        .filter(
            models.Asset.refill_date <= as_of_date,
            models.Asset.status == "Active",
        )
        .count()
    )

    # Locations that have an asset currently assigned
    locations_with_assets = (
        scoped_locations
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
        inspections_in_range=inspections_in_range,
        maintenance_in_range=maintenance_in_range,
        inspections_passed=inspections_passed,
        inspections_failed=inspections_failed,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/monthly-trend", response_model=List[schemas.MonthlyTrendItem])
def get_monthly_trend(
    months: int = 12,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    result = []
    today = datetime.utcnow()

    # If start_date and end_date are provided, determine the distinct months in that range
    if start_date and end_date:
        try:
            s_dt = datetime.strptime(start_date, "%Y-%m-%d")
            e_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # Build list of year-months in ascending order
            curr = s_dt.replace(day=1)
            target_end = e_dt.replace(day=1)
            month_targets = []
            while curr <= target_end:
                month_targets.append(curr)
                # Next month
                if curr.month == 12:
                    curr = curr.replace(year=curr.year + 1, month=1)
                else:
                    curr = curr.replace(month=curr.month + 1)

            # If month_targets is empty (start > end), fallback
            if not month_targets:
                month_targets = [s_dt.replace(day=1)]

            base_insp = apply_scope(db.query(models.Inspection), current_user, db, models.Inspection)
            base_maint = apply_scope(db.query(models.Maintenance), current_user, db, models.Maintenance)

            for target in month_targets:
                year = target.year
                month = target.month

                inspections = (
                    base_insp.filter(
                        extract("year", models.Inspection.inspection_date) == year,
                        extract("month", models.Inspection.inspection_date) == month,
                    )
                    .count()
                )

                passed = (
                    base_insp.filter(
                        extract("year", models.Inspection.inspection_date) == year,
                        extract("month", models.Inspection.inspection_date) == month,
                        models.Inspection.overall_status == "Pass",
                    )
                    .count()
                )

                failed = (
                    base_insp.filter(
                        extract("year", models.Inspection.inspection_date) == year,
                        extract("month", models.Inspection.inspection_date) == month,
                        models.Inspection.overall_status == "Fail",
                    )
                    .count()
                )

                maintenance = (
                    base_maint.filter(
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
        except Exception:
            pass  # Fallback to default month calculation if any parsing fails

    # Default calculation: past `months` months ending today
    base_insp = apply_scope(db.query(models.Inspection), current_user, db, models.Inspection)
    base_maint = apply_scope(db.query(models.Maintenance), current_user, db, models.Maintenance)

    for i in range(months - 1, -1, -1):
        target = today.replace(day=1) - timedelta(days=i * 28)
        year = target.year
        month = target.month

        inspections = (
            base_insp.filter(
                extract("year", models.Inspection.inspection_date) == year,
                extract("month", models.Inspection.inspection_date) == month,
            )
            .count()
        )

        passed = (
            base_insp.filter(
                extract("year", models.Inspection.inspection_date) == year,
                extract("month", models.Inspection.inspection_date) == month,
                models.Inspection.overall_status == "Pass",
            )
            .count()
        )

        failed = (
            base_insp.filter(
                extract("year", models.Inspection.inspection_date) == year,
                extract("month", models.Inspection.inspection_date) == month,
                models.Inspection.overall_status == "Fail",
            )
            .count()
        )

        maintenance = (
            base_maint.filter(
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
    scoped_locs = apply_scope(db.query(models.Location), current_user, db, models.Location)
    departments = scoped_locs.with_entities(models.Location.department).distinct().all()
    result = []

    for (dept,) in departments:
        if not dept:
            continue
        total = (
            scoped_locs
            .filter(
                models.Location.department == dept,
                models.Location.status == "Active",
            )
            .count()
        )
        installed = (
            scoped_locs
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

    scoped_locs = apply_scope(db.query(models.Location), current_user, db, models.Location)
    result = []
    for category in RISK_CATEGORIES:
        count = (
            scoped_locs
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
                "timestamp": log.timestamp.isoformat() if log.timestamp else datetime.utcnow().isoformat(),
            }
        )
    return create_api_response(True, "Dashboard data retrieved", {"activity": activity})


@router.get("/plant-wise")
def get_plant_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    scoped_locs = apply_scope(db.query(models.Location), current_user, db, models.Location)
    plants = scoped_locs.with_entities(models.Location.plant).distinct().all()
    result = []
    for (plant,) in plants:
        if not plant:
            continue
        total = (
            scoped_locs
            .filter(
                models.Location.plant == plant,
                models.Location.status == "Active",
            )
            .count()
        )
        installed = (
            scoped_locs
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
    base_assets = apply_scope(db.query(models.Asset), current_user, db, models.Asset)
    types = (
        base_assets.outerjoin(models.MasterAssetType, models.Asset.asset_type_id == models.MasterAssetType.id)
        .with_entities(
            func.coalesce(models.MasterAssetType.name, "Other").label("asset_type"),
            func.count(models.Asset.asset_id).label("count"),
        )
        .group_by(func.coalesce(models.MasterAssetType.name, "Other"))
        .all()
    )

    return [{"asset_type": t, "count": c} for t, c in types]


@router.get("/inspection-status-distribution", response_model=List[schemas.InspectionStatusItem])
def get_inspection_status_distribution(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    base = apply_scope(db.query(models.Inspection), current_user, db, models.Inspection)
    query = base.with_entities(
        models.Inspection.overall_status,
        func.count(models.Inspection.inspection_id).label("count")
    )
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(models.Inspection.inspection_date >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(models.Inspection.inspection_date <= end_dt)
        except ValueError:
            pass

    results = query.group_by(models.Inspection.overall_status).all()
    return [schemas.InspectionStatusItem(status=s if s else "Unknown", count=c) for s, c in results]


@router.get("/overdue-inspections")
def get_overdue_inspections(
    limit: int = 10,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    today = datetime.utcnow()
    overdue_list = []
    scoped_locs = apply_scope(db.query(models.Location), current_user, db, models.Location)
    locations = (
        scoped_locs
        .filter(
            models.Location.status == "Active",
            models.Location.inspection_frequency.is_not(None),
        )
        .all()
    )
    for loc in locations:
        asset_id = loc.assets[0].asset_id if loc.assets else None
        if loc.last_inspection_date is None:
            overdue_list.append({
                "location_id": loc.location_id,
                "location_name": loc.location_name,
                "last_inspection": None,
                "days_overdue": 999,
                "current_asset_id": asset_id,
                "department": loc.department,
                "area": loc.area
            })
        else:
            next_due = loc.last_inspection_date + timedelta(days=loc.inspection_frequency)
            if today > next_due:
                days = (today - next_due).days
                overdue_list.append({
                    "location_id": loc.location_id,
                    "location_name": loc.location_name,
                    "last_inspection": loc.last_inspection_date.isoformat(),
                    "days_overdue": days,
                    "current_asset_id": asset_id,
                    "department": loc.department,
                    "area": loc.area
                })
    overdue_list.sort(key=lambda x: x["days_overdue"], reverse=True)
    return overdue_list[:limit]


@router.get("/recent-maintenance")
def get_recent_maintenance(
    limit: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("view_dashboard")),
):
    query = apply_scope(db.query(models.Maintenance), current_user, db, models.Maintenance)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(models.Maintenance.opened_date >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(models.Maintenance.opened_date <= end_dt)
        except ValueError:
            pass

    tickets = (
        query.order_by(models.Maintenance.opened_date.desc().nullslast(), models.Maintenance.maintenance_id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "maintenance_id": t.maintenance_id,
            "asset_id": t.asset_id,
            "location_id": t.location_id,
            "issue": t.issue,
            "priority": t.priority,
            "status": t.status,
            "assigned_to": t.assigned_to,
            "opened_date": t.opened_date.isoformat() if t.opened_date else None,
        }
        for t in tickets
    ]
