"""Server-verified ad completion ledger.

The client can never say "I watched 35 ads". It can only report a completion
that carries a provider event id; the backend validates it, de-duplicates it,
stores it, and only then updates referral progress.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.db.base import utcnow
from app.models import (
    AdEvent,
    AdEventStatus,
    AuditAction,
    Referral,
    ReferralProgress,
    ReferralStatus,
    User,
)
from app.services import audit_service, milestone_service


def _reject(db: Session, user_id: str, provider: str, event_id: str, reason: str,
            device_hash: str = "", ip_hash: str = "") -> None:
    db.add(
        AdEvent(
            user_id=user_id,
            provider=provider,
            provider_event_id=f"{event_id}:rejected:{utcnow().timestamp()}",
            status=AdEventStatus.REJECTED,
            eligible=False,
            rejection_reason=reason,
            device_hash=device_hash,
            ip_hash=ip_hash,
        )
    )
    audit_service.log(
        db, AuditAction.AD_EVENT_REJECTED, "ad_event", None,
        actor_user_id=user_id, meta={"reason": reason, "provider": provider}, ip_hash=ip_hash,
    )
    db.flush()


def record_completion(
    db: Session,
    user: User,
    provider: str,
    provider_event_id: str,
    watched_seconds: int,
    ad_unit: Optional[str] = None,
    completed_at: Optional[datetime] = None,
    device_hash: str = "",
    ip_hash: str = "",
) -> Dict:
    """Validate + store an ad completion, then run the milestone engine."""
    # 1. Freshness check.
    if completed_at:
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        age = (utcnow() - completed_at).total_seconds()
        if age > settings.AD_EVENT_MAX_AGE_SECONDS or age < -60:
            _reject(db, user.id, provider, provider_event_id, "STALE_TIMESTAMP", device_hash, ip_hash)
            raise AppError(ErrorCode.AD_EVENT_REJECTED, "Ad completion event is not valid.", 400)

    # 2. Minimum watch duration.
    if watched_seconds < settings.AD_MIN_WATCH_SECONDS:
        _reject(db, user.id, provider, provider_event_id, "INSUFFICIENT_WATCH_TIME", device_hash, ip_hash)
        raise AppError(ErrorCode.AD_EVENT_REJECTED, "Ad was not watched completely.", 400)

    # 3. Duplicate detection (unique provider event id).
    duplicate = db.execute(
        select(AdEvent).where(
            AdEvent.provider == provider, AdEvent.provider_event_id == provider_event_id
        )
    ).scalar_one_or_none()
    if duplicate:
        return {
            "duplicate": True,
            "eligibleAds": eligible_ad_count(db, user.id),
            "creditedRewards": [],
        }

    event = AdEvent(
        user_id=user.id,
        provider=provider,
        provider_event_id=provider_event_id,
        ad_unit=ad_unit,
        watched_seconds=watched_seconds,
        status=AdEventStatus.VERIFIED,
        eligible=True,
        device_hash=device_hash,
        ip_hash=ip_hash,
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:  # concurrent duplicate
        db.rollback()
        return {
            "duplicate": True,
            "eligibleAds": eligible_ad_count(db, user.id),
            "creditedRewards": [],
        }

    audit_service.log(
        db, AuditAction.AD_EVENT_VERIFIED, "ad_event", event.id,
        actor_user_id=user.id, meta={"provider": provider, "eventId": provider_event_id},
        ip_hash=ip_hash,
    )

    total = eligible_ad_count(db, user.id)
    credited = sync_referral_progress(db, user.id, total)
    return {"duplicate": False, "eligibleAds": total, "creditedRewards": credited}


def eligible_ad_count(db: Session, user_id: str) -> int:
    return int(
        db.execute(
            select(func.count(AdEvent.id)).where(
                AdEvent.user_id == user_id,
                AdEvent.eligible.is_(True),
                AdEvent.status == AdEventStatus.VERIFIED,
            )
        ).scalar_one()
    )


def sync_referral_progress(db: Session, referred_user_id: str, total: Optional[int] = None):
    """Project the ad ledger onto the referral where this user is the referred party."""
    referral = db.execute(
        select(Referral).where(Referral.referred_user_id == referred_user_id)
    ).scalar_one_or_none()
    if referral is None:
        return []

    if total is None:
        total = eligible_ad_count(db, referred_user_id)

    progress = db.execute(
        select(ReferralProgress).where(ReferralProgress.referral_id == referral.id)
    ).scalar_one_or_none()
    if progress is None:
        progress = ReferralProgress(
            referral_id=referral.id, referred_user_id=referred_user_id, eligible_ads_watched=0
        )
        db.add(progress)
    progress.eligible_ads_watched = total
    progress.last_verified_at = utcnow()
    db.flush()

    if referral.status in ReferralStatus.BLOCKED:
        return []
    return milestone_service.evaluate(db, referral, ads_watched=total)
