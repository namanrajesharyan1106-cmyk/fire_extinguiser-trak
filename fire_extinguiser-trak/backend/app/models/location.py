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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

if TYPE_CHECKING:
    from .user import User
    from .asset import Asset
    from .inspection import Inspection
    from .maintenance import Maintenance


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

    # Asset Requirement
    required_asset_type: Mapped[Optional[str]] = mapped_column(String)
    required_capacity: Mapped[Optional[str]] = mapped_column(String)

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

    assets: Mapped[Optional["Asset"]] = relationship(
        "Asset",
        uselist=False,
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

    @property
    def current_asset_id(self) -> Optional[str]:
        return self.assets.asset_id if self.assets else None