from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User
    from .location import Location
    from .asset import Asset
    from .inspection import Inspection
    from .maintenance import Maintenance

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Maintenance(Base):
    __tablename__ = "maintenance"
    __table_args__ = (Index("ix_maintenance_maintenance_id", "maintenance_id"),)

    maintenance_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.asset_id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[str] = mapped_column(
        ForeignKey("locations.location_id", ondelete="CASCADE"), index=True
    )
    issue: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[Optional[str]] = mapped_column(String)
    assigned_to: Mapped[Optional[str]] = mapped_column(String)
    technician_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    verified_by: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(String)
    opened_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    completion_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    closed_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    inspection_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("inspection.inspection_id", ondelete="SET NULL"), index=True
    )
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    asset: Mapped[Optional["Asset"]] = relationship(
        "Asset", back_populates="maintenance"
    )
    inspection: Mapped[Optional["Inspection"]] = relationship(
        "Inspection", back_populates="maintenance"
    )
    location: Mapped[Optional["Location"]] = relationship(
        "Location", back_populates="maintenance"
    )
    technician: Mapped[Optional["User"]] = relationship(
        "User", back_populates="maintenance"
    )
