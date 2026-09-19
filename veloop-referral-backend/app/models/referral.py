from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ReferralStatus


class Referral(UUIDMixin, TimestampMixin, Base):
    """The referral relationship. `referred_user_id` is UNIQUE -> one referrer per user."""

    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint("referred_user_id", name="uq_referral_referred_user"),
        Index("ix_referrals_referrer_status", "referrer_user_id", "status"),
        Index("ix_referrals_created_at", "created_at"),
    )

    referrer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    referred_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    referral_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=ReferralStatus.PENDING, nullable=False, index=True)
    attribution_source: Mapped[str] = mapped_column(String(32), default="LINK", nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), default="LOW", nullable=False)
    device_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ReferralClick(UUIDMixin, TimestampMixin, Base):
    """A link click is tracked separately - a click is never a referral."""

    __tablename__ = "referral_clicks"
    __table_args__ = (Index("ix_clicks_code_created", "referral_code", "created_at"),)

    referral_code: Mapped[str] = mapped_column(String(16), nullable=False)
    referrer_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    device_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent_family: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    converted_referral_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class ReferralProgress(UUIDMixin, TimestampMixin, Base):
    """Projection of the authoritative ad-event ledger; never client-writable."""

    __tablename__ = "referral_progress"
    __table_args__ = (UniqueConstraint("referral_id", name="uq_progress_referral"),)

    referral_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("referrals.id", ondelete="CASCADE"), nullable=False
    )
    referred_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    eligible_ads_watched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
