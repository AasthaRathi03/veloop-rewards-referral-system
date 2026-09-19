"""Configurable milestone engine.

Milestone rules live in `milestone_configs` (DB). Adding/changing a milestone
is a config change, not a code change. Each (referral, milestone, reward_type)
can only ever be credited once - enforced by a UNIQUE constraint.
"""
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utcnow
from app.models import (
    AuditAction,
    MilestoneConfig,
    Referral,
    ReferralProgress,
    ReferralReward,
    ReferralStatus,
    RewardStatus,
)
from app.services import audit_service, reward_service

REGISTRATION_MILESTONE = 0  # awarded when a valid referral is attributed


def active_milestones(db: Session) -> List[MilestoneConfig]:
    return (
        db.execute(
            select(MilestoneConfig)
            .where(MilestoneConfig.active.is_(True))
            .order_by(MilestoneConfig.sort_order, MilestoneConfig.milestone)
        )
        .scalars()
        .all()
    )


def final_milestone(db: Session) -> int:
    rows = [m.milestone for m in active_milestones(db)]
    return max(rows) if rows else 0


def _reward_key(referral_id: str, milestone: int, reward_type: str) -> str:
    return f"referral:{referral_id}:m{milestone}:{reward_type}"


def _lock_referral(db: Session, referral_id: str) -> Referral:
    stmt = select(Referral).where(Referral.id == referral_id)
    if not settings.is_sqlite:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one()


def evaluate(db: Session, referral: Referral, ads_watched: Optional[int] = None) -> List[Dict]:
    """Credit every newly-reached milestone for a referral. Idempotent.

    The caller owns the surrounding transaction (commit/rollback).
    """
    referral = _lock_referral(db, referral.id)

    if referral.status in ReferralStatus.BLOCKED:
        return []  # spam / rejected / under review -> no rewards at all

    if ads_watched is None:
        progress = db.execute(
            select(ReferralProgress).where(ReferralProgress.referral_id == referral.id)
        ).scalar_one_or_none()
        ads_watched = progress.eligible_ads_watched if progress else 0

    credited: List[Dict] = []
    for config in active_milestones(db):
        if config.milestone > ads_watched:
            continue

        reward = db.execute(
            select(ReferralReward).where(
                ReferralReward.referral_id == referral.id,
                ReferralReward.milestone == config.milestone,
                ReferralReward.reward_type == config.reward_type,
            )
        ).scalar_one_or_none()

        if reward and reward.status == RewardStatus.CREDITED:
            continue  # already issued - never twice

        if reward is None:
            reward = ReferralReward(
                referral_id=referral.id,
                referrer_user_id=referral.referrer_user_id,
                reward_type=config.reward_type,
                reward_amount=config.reward_amount,
                milestone=config.milestone,
                status=RewardStatus.PENDING,
            )
            db.add(reward)
            try:
                db.flush()
            except IntegrityError:  # pragma: no cover - concurrent duplicate
                db.rollback()
                continue

        audit_service.log(
            db,
            AuditAction.MILESTONE_REACHED,
            "referral",
            referral.id,
            actor_user_id=referral.referrer_user_id,
            meta={"milestone": config.milestone, "rewardType": config.reward_type, "ads": ads_watched},
        )

        reason = (
            "Successful referral"
            if config.milestone == REGISTRATION_MILESTONE
            else f"Referral milestone {config.milestone} ads"
        )
        txn, created = reward_service.credit(
            db,
            user_id=referral.referrer_user_id,
            reward_type=config.reward_type,
            amount=config.reward_amount,
            reason=reason,
            idempotency_key=_reward_key(referral.id, config.milestone, config.reward_type),
            referral_id=referral.id,
            reward_id=reward.id,
            milestone=config.milestone,
        )
        reward.status = RewardStatus.CREDITED
        reward.credited_at = txn.created_at or utcnow()
        db.flush()

        if created:
            credited.append(
                {
                    "milestone": config.milestone,
                    "rewardType": config.reward_type,
                    "amount": config.reward_amount,
                    "label": config.label,
                    "transactionId": txn.id,
                }
            )

    _update_referral_status(db, referral, ads_watched)
    return credited


def _update_referral_status(db: Session, referral: Referral, ads_watched: int) -> None:
    if referral.status in ReferralStatus.BLOCKED:
        return
    last = final_milestone(db)
    if last and ads_watched >= last:
        if referral.status != ReferralStatus.SUCCESSFUL:
            referral.status = ReferralStatus.SUCCESSFUL
            referral.completed_at = utcnow()
            audit_service.log(
                db,
                AuditAction.REFERRAL_COMPLETED,
                "referral",
                referral.id,
                actor_user_id=referral.referrer_user_id,
                meta={"ads": ads_watched},
            )
    elif ads_watched > 0:
        referral.status = ReferralStatus.QUALIFYING
    db.flush()


def milestone_view(db: Session, ads_watched: int, credited_keys: set) -> List[Dict]:
    """Milestone list for the UI - unlocked/credited flags computed server side."""
    out = []
    for config in active_milestones(db):
        key = (config.milestone, config.reward_type)
        out.append(
            {
                "id": config.id,
                "milestone": config.milestone,
                "rewardType": config.reward_type,
                "rewardAmount": config.reward_amount,
                "label": config.label,
                "subtitle": config.subtitle,
                "condition": config.condition_text,
                "unlocked": ads_watched >= config.milestone,
                "credited": key in credited_keys,
            }
        )
    return out
