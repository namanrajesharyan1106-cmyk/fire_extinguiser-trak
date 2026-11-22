from dataclasses import dataclass
from typing import Optional, Set, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import false

from ..models.user import User, UserPlant
from ..models.location import Location
from ..models.asset import Asset
from ..models.inspection import Inspection
from ..models.maintenance import Maintenance


@dataclass
class Scope:
    plants: Optional[Set[str]]
    departments: Optional[Set[str]]

    @property
    def is_global(self) -> bool:
        return self.plants is None and self.departments is None

    @property
    def is_empty(self) -> bool:
        return self.plants is not None and len(self.plants) == 0


def get_user_scope(user: User, db: Session) -> Scope:
    """
    Determines user's plant and department scope.
    - ADMIN: global (plants=None, departments=None)
    - SAFETY HEAD: plant-scoped across all departments (departments=None)
    - Others: plant-scoped and department-scoped (if user.department set)
    - Fail-closed: non-admin without assigned plant gets plants=set()
    """
    if getattr(user, "role", None) == "ADMIN":
        return Scope(plants=None, departments=None)

    # Collect plants from UserPlant table and user.plant
    plants: Set[str] = set()
    user_plants = db.query(UserPlant).filter(UserPlant.user_id == user.id).all()
    for up in user_plants:
        if up.plant_name and up.plant_name.strip():
            plants.add(up.plant_name.strip())

    if getattr(user, "plant", None) and user.plant.strip():
        plants.add(user.plant.strip())

    if user.role == "SAFETY HEAD":
        return Scope(plants=plants, departments=None)

    departments: Optional[Set[str]] = None
    if getattr(user, "department", None) and user.department.strip():
        departments = {user.department.strip()}

    return Scope(plants=plants, departments=departments)


def apply_scope(query: Any, user: User, db: Session, model_class: Any) -> Any:
    """
    Applies plant and department scope filtering to a SQLAlchemy query.
    """
    scope = get_user_scope(user, db)
    if scope.is_global:
        return query
    if scope.is_empty:
        return query.filter(false())

    model_name = getattr(model_class, "__name__", "")

    if model_name == "Location":
        query = query.filter(Location.plant.in_(scope.plants))
        if scope.departments:
            query = query.filter(Location.department.in_(scope.departments))

    elif model_name == "Asset":
        query = query.filter(Asset.location.has(Location.plant.in_(scope.plants)))
        if scope.departments:
            query = query.filter(Asset.location.has(Location.department.in_(scope.departments)))

    elif model_name == "Inspection":
        query = query.filter(Inspection.location.has(Location.plant.in_(scope.plants)))
        if scope.departments:
            query = query.filter(Inspection.location.has(Location.department.in_(scope.departments)))

    elif model_name == "Maintenance":
        query = query.filter(Maintenance.location.has(Location.plant.in_(scope.plants)))
        if scope.departments:
            query = query.filter(Maintenance.location.has(Location.department.in_(scope.departments)))

    return query


def check_record_scope(record: Any, user: User, db: Session) -> bool:
    """
    Checks if a single DB record is within the user's scope.
    """
    scope = get_user_scope(user, db)
    if scope.is_global:
        return True
    if scope.is_empty:
        return False

    # Extract plant & department from record
    rec_plant = None
    rec_dept = None

    if hasattr(record, "plant"):
        rec_plant = getattr(record, "plant", None)
        rec_dept = getattr(record, "department", None)
    elif hasattr(record, "location") and record.location:
        rec_plant = getattr(record.location, "plant", None)
        rec_dept = getattr(record.location, "department", None)
    elif hasattr(record, "location_id") and record.location_id:
        loc = db.query(Location).filter(Location.location_id == record.location_id).first()
        if loc:
            rec_plant = loc.plant
            rec_dept = loc.department

    if not rec_plant or rec_plant not in scope.plants:
        return False

    if scope.departments and rec_dept not in scope.departments:
        return False

    return True


def validate_plant_param(plant_param: Optional[str], scope: Scope) -> Optional[str]:
    """
    Validates a plant query param against user's scope.
    """
    if scope.is_global:
        return plant_param
    if scope.is_empty:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. No plants assigned to user.",
        )
    if plant_param and plant_param.strip():
        cleaned = plant_param.strip()
        if cleaned not in scope.plants:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for plant '{cleaned}'. Not within your assigned scope.",
            )
        return cleaned
    return None
