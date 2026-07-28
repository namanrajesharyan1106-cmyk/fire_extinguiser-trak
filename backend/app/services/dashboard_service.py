from datetime import datetime, timedelta
from typing import List

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from ..core.constants import RISK_CATEGORIES
from ..models.asset import Asset
from ..models.audit import AuditLog
from ..models.inspection import Inspection
from ..models.location import Location
from ..models.maintenance import Maintenance
from ..models.user import User
from ..schemas import dashboard as schemas
from ..utils.asset_checks import is_asset_expired, is_refill_overdue


def _compliance_percent(total: int, compliant: int) -> float:
    if total == 0:
        return 0.0
    return round((compliant / total) * 100, 1)


def get_dashboard_stats(db: Session) -> schemas.DashboardStats:
    today = datetime.utcnow()
    today_date = today.date()

    total_locations = db.query(Location).filter(Location.status == "Active").count()
    total_assets = db.query(Asset).count()
    installed_assets = db.query(Asset).filter(Asset.location_id.is_not(None)).count()
    unassigned_assets = total_assets - installed_assets

    inspection_completed_today = (
        db.query(Inspection)
        .filter(func.date(Inspection.inspection_date) == today_date)
        .count()
    )

    inspection_due_today = 0
    overdue_inspections = 0
    active_locations = (
        db.query(Location)
        .filter(
            Location.status == "Active",
            Location.inspection_frequency.is_not(None),
        )
        .all()
    )

    for loc in active_locations:
        if loc.last_inspection_date is None:
            inspection_due_today += 1
            overdue_inspections += 1
        else:
            next_due = loc.last_inspection_date + timedelta(
                days=loc.inspection_frequency or 0
            )
            if today >= next_due:
                inspection_due_today += 1
            if today > next_due:
                overdue_inspections += 1

    open_maintenance = (
        db.query(Maintenance)
        .filter(Maintenance.status.notin_(["Closed", "Verified"]))
        .count()
    )

    expired_assets = 0
    refill_due = 0
    all_active_assets = db.query(Asset).filter(Asset.status == "Active").all()
    for asset in all_active_assets:
        if is_asset_expired(asset):
            expired_assets += 1
        if is_refill_overdue(asset):
            refill_due += 1

    locations_with_assets = (
        db.query(Asset).filter(Asset.location_id.is_not(None)).count()
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


def get_monthly_trend(db: Session, months: int = 12) -> List[schemas.MonthlyTrendItem]:
    result = []
    today = datetime.utcnow()

    for i in range(months - 1, -1, -1):
        target = today.replace(day=1) - timedelta(days=i * 28)
        year = target.year
        month = target.month

        inspections = (
            db.query(Inspection)
            .filter(
                extract("year", Inspection.inspection_date) == year,
                extract("month", Inspection.inspection_date) == month,
            )
            .count()
        )

        passed = (
            db.query(Inspection)
            .filter(
                extract("year", Inspection.inspection_date) == year,
                extract("month", Inspection.inspection_date) == month,
                Inspection.overall_status == "Pass",
            )
            .count()
        )

        failed = (
            db.query(Inspection)
            .filter(
                extract("year", Inspection.inspection_date) == year,
                extract("month", Inspection.inspection_date) == month,
                Inspection.overall_status == "Fail",
            )
            .count()
        )

        maintenance = (
            db.query(Maintenance)
            .filter(
                extract("year", Maintenance.opened_date) == year,
                extract("month", Maintenance.opened_date) == month,
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


def get_department_stats(db: Session) -> List[schemas.DepartmentStatsItem]:
    departments = db.query(Location.department).distinct().all()
    result = []

    for (dept,) in departments:
        if not dept:
            continue
        total = (
            db.query(Location)
            .filter(
                Location.department == dept,
                Location.status == "Active",
            )
            .count()
        )
        # Find assets that belong to a location with this department
        installed = (
            db.query(Asset)
            .join(Location, Asset.location_id == Location.location_id)
            .filter(
                Location.department == dept,
                Location.status == "Active",
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


def get_risk_stats(db: Session) -> List[schemas.RiskStatsItem]:
    result = []
    for category in RISK_CATEGORIES:
        count = (
            db.query(Location)
            .filter(
                Location.risk_category == category,
                Location.status == "Active",
            )
            .count()
        )
        result.append(schemas.RiskStatsItem(risk_category=category, count=count))
    return result


def get_recent_activity(db: Session, limit: int = 20):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    activity = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        activity.append(
            {
                "id": log.id,
                "action": log.action,
                "table": log.table_name,
                "record_id": log.record_id,
                "user": user.name if user else "System",
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
        )
    return {"activity": activity}


def get_plant_stats(db: Session):
    plants = db.query(Location.plant).distinct().all()
    result = []
    for (plant,) in plants:
        if not plant:
            continue
        total = (
            db.query(Location)
            .filter(
                Location.plant == plant,
                Location.status == "Active",
            )
            .count()
        )
        installed = (
            db.query(Asset)
            .join(Location, Asset.location_id == Location.location_id)
            .filter(
                Location.plant == plant,
                Location.status == "Active",
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


def get_asset_type_distribution(db: Session):
    types = (
        db.query(Asset.asset_type, func.count(Asset.asset_id).label("count"))
        .group_by(Asset.asset_type)
        .all()
    )

    return [{"asset_type": t, "count": c} for t, c in types]
