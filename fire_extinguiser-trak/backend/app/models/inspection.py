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


class Inspection(Base):
    __tablename__ = "inspection"
    __table_args__ = (Index("ix_inspection_inspection_id", "inspection_id"),)

    inspection_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inspection_no: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    location_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("locations.location_id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("assets.asset_id", ondelete="SET NULL"), index=True
    )
    inspector: Mapped[Optional[str]] = mapped_column(String)
    inspector_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    inspection_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    pressure: Mapped[Optional[str]] = mapped_column(String)
    seal: Mapped[Optional[str]] = mapped_column(String)
    hose: Mapped[Optional[str]] = mapped_column(String)
    pin: Mapped[Optional[str]] = mapped_column(String)
    gauge: Mapped[Optional[str]] = mapped_column(String)
    nozzle: Mapped[Optional[str]] = mapped_column(String)
    mounting: Mapped[Optional[str]] = mapped_column(String)
    visibility: Mapped[Optional[str]] = mapped_column(String)
    accessibility: Mapped[Optional[str]] = mapped_column(String)
    safety_tag: Mapped[Optional[str]] = mapped_column(String)
    cylinder_damage: Mapped[Optional[str]] = mapped_column(String)
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    photo: Mapped[Optional[str]] = mapped_column(String)
    overall_status: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    asset: Mapped[Optional["Asset"]] = relationship(
        "Asset", back_populates="inspection"
    )
    inspector_: Mapped[Optional["User"]] = relationship(
        "User", back_populates="inspection"
    )
    location: Mapped[Optional["Location"]] = relationship(
        "Location", back_populates="inspection"
    )
    maintenance: Mapped[list["Maintenance"]] = relationship(
        "Maintenance", back_populates="inspection"
    )
