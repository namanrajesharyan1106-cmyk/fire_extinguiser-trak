from typing import TYPE_CHECKING, Optional
import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

if TYPE_CHECKING:
    from .user import User
    from .asset import Asset
    from .inspection import Inspection
    from .maintenance import Maintenance
    from .system import MasterAssetType, MasterCapacityType


class Location(Base):
    __tablename__ = "locations"

    __table_args__ = (
        ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_locations_created_by_users",
        ),
        UniqueConstraint(
            "location_name",
            "plant",
            name="uq_location_name_plant",
        ),
        Index("ix_locations_department", "department"),
        Index("ix_locations_location_code", "location_code", unique=True),
        Index("ix_locations_location_id", "location_id"),
        Index("ix_locations_location_name", "location_name"),
        Index("ix_locations_plant", "plant"),
    )

    # Primary Key
    location_id: Mapped[str] = mapped_column(String, primary_key=True)

    # Basic Details
    location_name: Mapped[str] = mapped_column(String, nullable=False)
    location_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # QR
    qr_code: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
    )

    qr_image_path: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    # Plant Details
    plant: Mapped[Optional[str]] = mapped_column(String)
    area: Mapped[Optional[str]] = mapped_column(String)
    department: Mapped[Optional[str]] = mapped_column(String)
    building: Mapped[Optional[str]] = mapped_column(String)
    floor: Mapped[Optional[str]] = mapped_column(String)
    machine: Mapped[Optional[str]] = mapped_column(String)

    # Master Data Foreign Keys
    required_asset_type_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("master_asset_types.id", ondelete="SET NULL"), index=True)
    required_capacity_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("master_capacity_types.id", ondelete="SET NULL"), index=True)

    # Safety
    risk_category: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(String)

    inspection_frequency: Mapped[Optional[int]] = mapped_column(Integer)
    last_inspection_date: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime
    )

    # GPS
    gps_lat: Mapped[Optional[float]] = mapped_column(Float)
    gps_lng: Mapped[Optional[float]] = mapped_column(Float)

    # Audit
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    created_by_id: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="locations",
    )

    max_assets: Mapped[int] = mapped_column(Integer, default=15)

    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        uselist=True,
        back_populates="location",
    )

    inspection: Mapped[list["Inspection"]] = relationship(
        "Inspection",
        back_populates="location",
        cascade="all, delete-orphan",
    )

    maintenance: Mapped[list["Maintenance"]] = relationship(
        "Maintenance",
        back_populates="location",
        cascade="all, delete-orphan",
    )

    required_asset_type_rel: Mapped[Optional["MasterAssetType"]] = relationship("MasterAssetType")
    required_capacity_rel: Mapped[Optional["MasterCapacityType"]] = relationship("MasterCapacityType")

    @property
    def required_asset_type(self) -> Optional[str]:
        return self.required_asset_type_rel.name if self.required_asset_type_rel else None

    @property
    def required_capacity(self) -> Optional[str]:
        return self.required_capacity_rel.name if self.required_capacity_rel else None

    @property
    def current_assets_count(self) -> int:
        return len(self.assets) if self.assets else 0

    @property
    def remaining_capacity(self) -> int:
        return max(0, self.max_assets - self.current_assets_count)