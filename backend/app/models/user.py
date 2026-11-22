from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User
    from .location import Location
    from .inspection import Inspection
    from .maintenance import Maintenance
    from .audit import AuditLog, Notification, Attachment
    from .auth import RefreshToken, PasswordHistory

import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class UserPlant(Base):
    __tablename__ = "user_plants"
    __table_args__ = (
        Index("ix_user_plants_id", "id"),
        Index("ix_user_plants_user_id", "user_id"),
        Index("ix_user_plants_plant_name", "plant_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plant_name: Mapped[str] = mapped_column(String)

    user: Mapped["User"] = relationship("User", back_populates="user_plants")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
        Index("ix_users_employee_id", "employee_id", unique=True),
        Index("ix_users_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[Optional[str]] = mapped_column(String)
    name: Mapped[Optional[str]] = mapped_column(String)
    email: Mapped[Optional[str]] = mapped_column(String)
    password_hash: Mapped[Optional[str]] = mapped_column(String)
    department: Mapped[Optional[str]] = mapped_column(String)
    plant: Mapped[Optional[str]] = mapped_column(String)
    role: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    is_first_login: Mapped[Optional[bool]] = mapped_column(Boolean)
    failed_login_attempts: Mapped[Optional[int]] = mapped_column(Integer)
    last_failed_login: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String)
    last_login_device: Mapped[Optional[str]] = mapped_column(String)
    last_login: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    locked_until: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="users"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )
    locations: Mapped[list["Location"]] = relationship(
        "Location", back_populates="created_by"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
    password_history: Mapped[list["PasswordHistory"]] = relationship(
        "PasswordHistory", back_populates="user"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user"
    )
    inspection: Mapped[list["Inspection"]] = relationship(
        "Inspection", back_populates="inspector_"
    )
    maintenance: Mapped[list["Maintenance"]] = relationship(
        "Maintenance", back_populates="technician"
    )
    user_plants: Mapped[list["UserPlant"]] = relationship(
        "UserPlant", back_populates="user", cascade="all, delete-orphan"
    )
