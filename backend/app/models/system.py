from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .system import Plant, Department, SystemConfig

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Plant(Base):
    __tablename__ = "plants"
    __table_args__ = (
        Index("ix_plants_id", "id"),
        Index("ix_plants_plant_code", "plant_code", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plant_code: Mapped[Optional[str]] = mapped_column(String)
    plant_name: Mapped[Optional[str]] = mapped_column(String)
    address: Mapped[Optional[str]] = mapped_column(String)
    contact: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    departments: Mapped[list["Department"]] = relationship(
        "Department", back_populates="plant"
    )


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        Index("ix_departments_dept_code", "dept_code", unique=True),
        Index("ix_departments_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dept_code: Mapped[Optional[str]] = mapped_column(String)
    dept_name: Mapped[Optional[str]] = mapped_column(String)
    plant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE")
    )
    head_name: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    plant: Mapped[Optional["Plant"]] = relationship(
        "Plant", back_populates="departments"
    )


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
