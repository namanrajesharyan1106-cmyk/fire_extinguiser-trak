from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .system import MasterPlant, MasterDepartment, SystemConfig

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

class MasterPlant(Base):
    __tablename__ = "master_plants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class MasterDepartment(Base):
    __tablename__ = "master_departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class SystemConfig(Base):
    __tablename__ = "system_config"
    __table_args__ = (
        Index("ix_system_config_id", "id"),
        Index("ix_system_config_key", "key", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[Optional[str]] = mapped_column(String)
    value: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String)

class SequenceTracker(Base):
    __tablename__ = "sequence_tracker"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String, index=True)
    plant: Mapped[Optional[str]] = mapped_column(String, index=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)


class MasterArea(Base):
    __tablename__ = "master_areas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class MasterBuilding(Base):
    __tablename__ = "master_buildings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class MasterFloor(Base):
    __tablename__ = "master_floors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class MasterAssetType(Base):
    __tablename__ = "master_asset_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class MasterCapacityType(Base):
    __tablename__ = "master_capacity_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class MasterRiskCategory(Base):
    __tablename__ = "master_risk_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class MasterInspectionFrequency(Base):
    __tablename__ = "master_inspection_frequencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
