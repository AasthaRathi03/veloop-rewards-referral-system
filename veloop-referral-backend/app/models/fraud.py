from typing import Optional

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class SpamReferral(UUIDMixin, TimestampMixin, Base):
    """Internal fraud evidence. Never returned to normal users in raw form."""

    __tablename__ = "spam_referrals"
    __table_args__ = (Index("ix_spam_referrer", "referrer_user_id"),)

    referral_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    referrer_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    referred_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_category: Mapped[str] = mapped_column(String(32), default="REFERRAL_ABUSE", nullable=False)
    device_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="BLOCKED", nullable=False)
