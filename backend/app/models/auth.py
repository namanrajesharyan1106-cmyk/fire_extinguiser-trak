from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User
    from .auth import RefreshToken, PasswordHistory

import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_id", "id"),
        Index("ix_refresh_tokens_token_hash", "token_hash", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[Optional[str]] = mapped_column(String)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    device_name: Mapped[Optional[str]] = mapped_column(String)
    ip_address: Mapped[Optional[str]] = mapped_column(String)
    is_revoked: Mapped[Optional[bool]] = mapped_column(Boolean)
    revoked_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="refresh_tokens"
    )


class PasswordHistory(Base):
    __tablename__ = "password_history"
    __table_args__ = (Index("ix_password_history_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    password_hash: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="password_history"
    )
