"""
Search router — global search across assets, locations, inspections, maintenance, users.
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import database
from ..core import dependencies as auth
from .auth import create_api_response

router = APIRouter()

@router.get("/", response_model=schemas.APIResponse[List[schemas.SearchResult]])
def global_search(
    q: str = Query(..., min_length=2, description="Search query (min 2 characters)"),
    limit: int = 20,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.require_permission("global_search")),
):
    results: List[schemas.SearchResult] = []
    search_term = f"%{q}%"

    # ── Assets ────────────────────────────────────────────────────────────────
    assets = (
        db.query(models.Asset)
        .filter(
            (models.Asset.asset_id.ilike(search_term))
            | (models.Asset.serial_number.ilike(search_term))
            | (models.Asset.asset_type.ilike(search_term))
            | (models.Asset.barcode.ilike(search_term))
        )
        .limit(limit // 2)
        .all()
    )

    for asset in assets:
        results.append(
            schemas.SearchResult(
                type="asset",
                id=asset.asset_id,
                title=f"Asset: {asset.asset_id}",
                subtitle=f"{asset.asset_type} • S/N: {asset.serial_number}",
                status=asset.status,
                url=f"/assets?highlight={asset.asset_id}",
            )
        )

    # ── Locations ─────────────────────────────────────────────────────────────
    locations = (
        db.query(models.Location)
        .filter(
            (models.Location.location_id.ilike(search_term))
            | (models.Location.location_name.ilike(search_term))
            | (models.Location.location_code.ilike(search_term))
            | (models.Location.department.ilike(search_term))
            | (models.Location.plant.ilike(search_term))
            | (models.Location.area.ilike(search_term))
            | (models.Location.machine.ilike(search_term))
            | (models.Location.qr_code.ilike(search_term))
        )
        .limit(limit // 2)
        .all()
    )

    for loc in locations:
        results.append(
            schemas.SearchResult(
                type="location",
                id=loc.location_id,
                title=f"Location: {loc.location_name}",
                subtitle=f"{loc.plant or ''} • {loc.department or ''} • {loc.area or ''}",
                status=loc.status,
                url=f"/locations?highlight={loc.location_id}",
            )
        )

    # ── Maintenance ───────────────────────────────────────────────────────────
    maintenance = (
        db.query(models.Maintenance)
        .filter(
            (models.Maintenance.issue.ilike(search_term))
            | (models.Maintenance.asset_id.ilike(search_term))
            | (models.Maintenance.assigned_to.ilike(search_term))
        )
        .limit(5)
        .all()
    )

    for m in maintenance:
        results.append(
            schemas.SearchResult(
                type="maintenance",
                id=str(m.maintenance_id),
                title=f"Ticket #{m.maintenance_id}: {(m.issue or '')[:50]}",
                subtitle=f"Asset: {m.asset_id} • Priority: {m.priority}",
                status=m.status,
                url=f"/maintenance?ticket={m.maintenance_id}",
            )
        )

    # ── Users (ADMIN only) ────────────────────────────────────────────────────
    if current_user.role in ["ADMIN", "IT ADMIN"]:
        users = (
            db.query(models.User)
            .filter(
                (models.User.name.ilike(search_term))
                | (models.User.email.ilike(search_term))
                | (models.User.employee_id.ilike(search_term))
                | (models.User.department.ilike(search_term))
            )
            .limit(5)
            .all()
        )

        for u in users:
            results.append(
                schemas.SearchResult(
                    type="user",
                    id=str(u.id),
                    title=f"User: {u.name}",
                    subtitle=f"{u.role} • {u.department}",
                    status=u.status,
                    url=f"/admin/users?user={u.id}",
                )
            )

    return create_api_response(True, "Search successful", results[:limit])
