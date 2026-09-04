from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .location import Location
    from .asset import Asset, AssetHistory
    from .inspection import Inspection
    from .maintenance import Maintenance

import datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_asset_id", "asset_id"),
        Index("ix_assets_serial_number", "serial_number", unique=True),
    )

    asset_id: Mapped[str] = mapped_column(String, primary_key=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String)
    asset_number: Mapped[Optional[str]] = mapped_column(String, unique=True)
    asset_type: Mapped[Optional[str]] = mapped_column(String)
    capacity: Mapped[Optional[str]] = mapped_column(String)
    manufacturer: Mapped[Optional[str]] = mapped_column(String)
    manufacturing_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    refill_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    expiry_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    amc_due_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    inspection_frequency: Mapped[Optional[int]] = mapped_column(Integer)
    barcode: Mapped[Optional[str]] = mapped_column(String)
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    photo: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    location_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("locations.location_id", ondelete="SET NULL"), index=True
    )

    location: Mapped[Optional["Location"]] = relationship(
        "Location", back_populates="assets"
    )
    asset_history: Mapped[list["AssetHistory"]] = relationship(
        "AssetHistory", back_populates="asset"
    )
    inspection: Mapped[list["Inspection"]] = relationship(
        "Inspection", back_populates="asset"
    )
    maintenance: Mapped[list["Maintenance"]] = relationship(
        "Maintenance", back_populates="asset"
    )

    @property
    def current_location_id(self) -> Optional[str]:
        return self.location_id


class AssetHistory(Base):
    __tablename__ = "asset_history"
    __table_args__ = (Index("ix_asset_history_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("assets.asset_id", ondelete="CASCADE")
    )
    old_location_id: Mapped[Optional[str]] = mapped_column(String)
    new_location_id: Mapped[Optional[str]] = mapped_column(String)
    movement_type: Mapped[Optional[str]] = mapped_column(String)
    movement_reason: Mapped[Optional[str]] = mapped_column(String)
    approval_by: Mapped[Optional[str]] = mapped_column(String)
    comments: Mapped[Optional[str]] = mapped_column(Text)
    movement_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    changed_by: Mapped[Optional[str]] = mapped_column(String)

    asset: Mapped[Optional["Asset"]] = relationship(
        "Asset", back_populates="asset_history"
    )
