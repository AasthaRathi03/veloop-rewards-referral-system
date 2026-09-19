from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin, utcnow


class User(UUIDMixin, TimestampMixin, Base):
    """Platform user. Balances are only ever mutated inside a reward transaction."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)

    # balances / ledgers
    sve_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gem_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spin_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    BALANCE_FIELD = {
        "SVE": "sve_balance",
        "TOKENS": "token_balance",
        "GEMS": "gem_balance",
        "SPINS": "spin_balance",
        "XP": "xp",
    }


class Device(UUIDMixin, TimestampMixin, Base):
    """A device identity derived from layered signals (stored only as an HMAC)."""

    __tablename__ = "devices"

    device_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    first_ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent_family: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    account_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class UserDevice(UUIDMixin, TimestampMixin, Base):
    """Many-to-many association between accounts and devices."""

    __tablename__ = "user_devices"
    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_user_device"),
        Index("ix_user_devices_device", "device_id"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
