from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User
    from .audit import AuditLog, Notification, Attachment

import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[Optional[str]] = mapped_column(String)
    table_name: Mapped[Optional[str]] = mapped_column(String)
    record_id: Mapped[Optional[str]] = mapped_column(String)
    old_values: Mapped[Optional[str]] = mapped_column(Text)
    new_values: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String)
    device: Mapped[Optional[str]] = mapped_column(String)
    browser: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(String)
    timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[Optional[str]] = mapped_column(String)
    message: Mapped[Optional[str]] = mapped_column(String)
    is_read: Mapped[Optional[bool]] = mapped_column(Boolean)
    related_id: Mapped[Optional[str]] = mapped_column(String)
    related_type: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="notifications"
    )


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        Index("ix_attachments_id", "id"),
        Index("ix_attachments_related_id", "related_id"),
        Index("ix_attachments_related_type", "related_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    related_id: Mapped[Optional[str]] = mapped_column(String)
    related_type: Mapped[Optional[str]] = mapped_column(String)
    file_path: Mapped[Optional[str]] = mapped_column(String)
    file_type: Mapped[Optional[str]] = mapped_column(String)
    label: Mapped[Optional[str]] = mapped_column(String)
    uploaded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    users: Mapped[Optional["User"]] = relationship("User", back_populates="attachments")
