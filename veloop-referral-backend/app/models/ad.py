from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import AdEventStatus


class AdEvent(UUIDMixin, TimestampMixin, Base):
    """Server-verified ad completion ledger - the only source of ad progress."""

    __tablename__ = "ad_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_ad_event_provider_id"),
        Index("ix_ad_events_user_eligible", "user_id", "eligible"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ad_unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    watched_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=AdEventStatus.VERIFIED, nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    device_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
