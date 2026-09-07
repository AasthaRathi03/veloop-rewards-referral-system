from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database import Base
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, unique=True, nullable=True)
    referral_code = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)

    referrer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    referred_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, unique=True
    )

    referral_code = Column(String, nullable=False)

    status = Column(String, default="PENDING", nullable=False)

    attribution_source = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    completed_at = Column(DateTime, nullable=True)


class AdEvent(Base):
    __tablename__ = "ad_events"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    referral_id = Column(Integer, ForeignKey("referrals.id"), nullable=False)

    event_id = Column(String, unique=True, nullable=False)

    status = Column(String, default="VERIFIED", nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ReferralProgress(Base):
    __tablename__ = "referral_progress"

    id = Column(Integer, primary_key=True, index=True)

    referral_id = Column(
        Integer, ForeignKey("referrals.id"), unique=True, nullable=False
    )

    referred_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    eligible_ads_watched = Column(Integer, default=0, nullable=False)

    last_verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
