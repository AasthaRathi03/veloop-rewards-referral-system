from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import RewardStatus


class MilestoneConfig(UUIDMixin, TimestampMixin, Base):
    """Reward rules live in the DB, not in React and not in Python constants."""

    __tablename__ = "milestone_configs"
    __table_args__ = (
        UniqueConstraint("milestone", "reward_type", name="uq_milestone_reward_type"),
    )

    # milestone = required eligible ad watches; 0 = granted on successful attribution
    milestone: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_type: Mapped[str] = mapped_column(String(16), nullable=False)
    reward_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    condition_text: Mapped[str] = mapped_column(String(160), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ReferralReward(UUIDMixin, TimestampMixin, Base):
    """One row per (referral, milestone, reward_type) - DB-level idempotency."""

    __tablename__ = "referral_rewards"
    __table_args__ = (
        UniqueConstraint("referral_id", "milestone", "reward_type", name="uq_reward_once"),
        Index("ix_rewards_referrer", "referrer_user_id"),
    )

    referral_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("referrals.id", ondelete="CASCADE"), nullable=False
    )
    referrer_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reward_type: Mapped[str] = mapped_column(String(16), nullable=False)
    reward_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    milestone: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=RewardStatus.PENDING, nullable=False)
    credited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class RewardTransaction(UUIDMixin, TimestampMixin, Base):
    """Immutable ledger. Balances are derived from and reconciled against this."""

    __tablename__ = "reward_transactions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_txn_idempotency"),
        Index("ix_txn_user_type", "user_id", "reward_type"),
        Index("ix_txn_source", "source"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    referral_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reward_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reward_type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    milestone: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="REFERRAL", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=RewardStatus.CREDITED, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(190), nullable=False)


class IdempotencyRecord(UUIDMixin, TimestampMixin, Base):
    """Request-level idempotency (Idempotency-Key header) for reward-triggering calls."""

    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("scope", "user_id", "key", name="uq_idempotency_request"),
    )

    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
