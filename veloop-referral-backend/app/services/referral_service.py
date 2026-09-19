"""Referral attribution, dashboard and listings."""
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.db.base import utcnow
from app.models import (
    AuditAction,
    Referral,
    ReferralClick,
    ReferralProgress,
    ReferralReward,
    ReferralStatus,
    RewardStatus,
    RewardType,
    SpamReferral,
    User,
)
from app.services import audit_service, fraud_service, milestone_service, reward_service
from app.services.device_service import ResolvedDevice
from app.utils.codes import normalize_code
from app.utils.email_mask import mask_email


# --------------------------------------------------------------------------
# attribution
# --------------------------------------------------------------------------
def track_click(db: Session, code: str, device_hash: str, ip_hash: str, ua_family: str) -> str:
    """A click is recorded but is NOT a referral (spec 87/88)."""
    code = normalize_code(code)
    referrer = db.execute(select(User).where(User.referral_code == code)).scalar_one_or_none()
    click = ReferralClick(
        referral_code=code,
        referrer_user_id=referrer.id if referrer else None,
        device_hash=device_hash,
        ip_hash=ip_hash,
        user_agent_family=ua_family,
    )
    db.add(click)
    db.flush()
    audit_service.log(
        db, AuditAction.REFERRAL_CLICK, "referral_click", click.id,
        meta={"code": code, "known": bool(referrer)}, ip_hash=ip_hash,
    )
    return click.id


def find_referrer(db: Session, code: str) -> User:
    referrer = db.execute(
        select(User).where(User.referral_code == normalize_code(code))
    ).scalar_one_or_none()
    if referrer is None or referrer.status != "ACTIVE":
        raise AppError(ErrorCode.INVALID_REFERRAL_CODE, "This referral code is not valid.", 400)
    return referrer


def guard_pre_registration(
    db: Session, code: str, device: ResolvedDevice, email: str, phone: Optional[str]
) -> Tuple[User, fraud_service.RiskAssessment]:
    """Runs BEFORE the account exists.

    If the device is already tied to the referrer's own account we block the
    registration with SELF_REFERRAL_DETECTED so the frontend can show the
    "account already exists" modal.
    """
    referrer = find_referrer(db, code)
    risk = fraud_service.assess_referral_risk(
        db,
        referrer=referrer,
        device=device.device,
        ip_hash=device.ip_hash,
        candidate_email=email,
        candidate_phone=phone,
        token_mismatch=device.token_mismatch,
    )
    if risk.self_referral and "DEVICE_BELONGS_TO_REFERRER" in risk.reasons:
        fraud_service.record_spam(
            db,
            referrer_user_id=referrer.id,
            risk=risk,
            device_hash=device.device_hash,
            ip_hash=device.ip_hash,
            status="BLOCKED_AT_SIGNUP",
        )
        audit_service.log(
            db, AuditAction.SELF_REFERRAL_DETECTED, "user", referrer.id,
            meta={"riskScore": risk.score, "reasons": risk.reasons}, ip_hash=device.ip_hash,
        )
        db.commit()
        raise AppError(
            ErrorCode.SELF_REFERRAL_DETECTED,
            "This device has already been associated with a VELOOP Rewards account. "
            "Please use that account to log in.",
            409,
            extra={"maskedEmail": mask_email(referrer.email)},
        )
    return referrer, risk


def attribute(
    db: Session,
    referred_user: User,
    code: str,
    device: ResolvedDevice,
    source: str = "LINK",
    precomputed: Optional[Tuple[User, fraud_service.RiskAssessment]] = None,
) -> Referral:
    """Create the (immutable) referral relationship for `referred_user`."""
    existing = db.execute(
        select(Referral).where(Referral.referred_user_id == referred_user.id)
    ).scalar_one_or_none()
    if existing:
        # Attribution is immutable: a second code can never overwrite the first.
        raise AppError(
            ErrorCode.REFERRAL_ALREADY_ASSIGNED,
            "Your account is already linked to a referrer.",
            409,
        )

    if precomputed:
        referrer, risk = precomputed
    else:
        referrer = find_referrer(db, code)
        risk = fraud_service.assess_referral_risk(
            db,
            referrer=referrer,
            device=device.device,
            ip_hash=device.ip_hash,
            candidate_email=referred_user.email,
            candidate_phone=referred_user.phone,
            candidate_user=referred_user,
            token_mismatch=device.token_mismatch,
        )

    if referrer.id == referred_user.id:
        raise AppError(
            ErrorCode.SELF_REFERRAL_DETECTED,
            "You cannot refer yourself.",
            400,
            extra={"maskedEmail": mask_email(referrer.email)},
        )

    status = fraud_service.status_for_risk(risk)
    referral = Referral(
        referrer_user_id=referrer.id,
        referred_user_id=referred_user.id,
        referral_code=referrer.referral_code,
        status=status,
        attribution_source=source,
        risk_score=risk.score,
        risk_level=risk.level,
        device_id=device.device.id,
    )
    db.add(referral)
    try:
        db.flush()
    except IntegrityError:  # pragma: no cover - concurrent attribution
        db.rollback()
        raise AppError(
            ErrorCode.REFERRAL_ALREADY_ASSIGNED, "Your account is already linked to a referrer.", 409
        )

    db.add(
        ReferralProgress(
            referral_id=referral.id, referred_user_id=referred_user.id, eligible_ads_watched=0
        )
    )
    db.flush()

    audit_service.log(
        db, AuditAction.REFERRAL_CREATED, "referral", referral.id,
        actor_user_id=referred_user.id,
        meta={"referrer": referrer.id, "status": status, "riskLevel": risk.level},
        ip_hash=device.ip_hash,
    )

    if status in ReferralStatus.BLOCKED:
        fraud_service.record_spam(
            db,
            referrer_user_id=referrer.id,
            risk=risk,
            referral_id=referral.id,
            referred_user_id=referred_user.id,
            device_hash=device.device_hash,
            ip_hash=device.ip_hash,
            status="BLOCKED" if status == ReferralStatus.SPAM else "UNDER_REVIEW",
        )
        audit_service.log(
            db, AuditAction.REFERRAL_REJECTED, "referral", referral.id,
            meta={"status": status, "riskScore": risk.score}, ip_hash=device.ip_hash,
        )
        return referral

    # Valid referral -> registration reward (+20 XP) via the milestone engine.
    milestone_service.evaluate(db, referral, ads_watched=0)

    # Link any earlier click for funnel analytics.
    click = db.execute(
        select(ReferralClick)
        .where(
            ReferralClick.referral_code == referrer.referral_code,
            ReferralClick.device_hash == device.device_hash,
            ReferralClick.converted_referral_id.is_(None),
        )
        .order_by(ReferralClick.created_at.desc())
    ).scalars().first()
    if click:
        click.converted_referral_id = referral.id
        db.flush()

    return referral


# --------------------------------------------------------------------------
# read models
# --------------------------------------------------------------------------
def referral_link(code: str) -> str:
    return f"{settings.REFERRAL_LINK_BASE}?ref={code}"


def statistics(db: Session, user_id: str) -> Dict[str, int]:
    rows = db.execute(
        select(Referral.status, func.count(Referral.id))
        .where(Referral.referrer_user_id == user_id)
        .group_by(Referral.status)
    ).all()
    by_status = {r[0]: int(r[1]) for r in rows}

    successful = by_status.get(ReferralStatus.SUCCESSFUL, 0)
    pending = by_status.get(ReferralStatus.PENDING, 0) + by_status.get(ReferralStatus.QUALIFYING, 0)
    spam = (
        by_status.get(ReferralStatus.SPAM, 0)
        + by_status.get(ReferralStatus.REJECTED, 0)
        + by_status.get(ReferralStatus.FRAUD_REVIEW, 0)
    )
    return {
        "totalReferrals": successful + pending,   # valid relationships only
        "successfulReferrals": successful,
        "pendingReferrals": pending,
        "spamReferrals": spam,
    }


def _credited_keys(db: Session, referral_id: str) -> set:
    rows = db.execute(
        select(ReferralReward.milestone, ReferralReward.reward_type).where(
            ReferralReward.referral_id == referral_id,
            ReferralReward.status == RewardStatus.CREDITED,
        )
    ).all()
    return {(int(r[0]), r[1]) for r in rows}


def credited_keys_for_referrer(db: Session, user_id: str) -> set:
    """Milestones this referrer has already been paid for (any referral)."""
    rows = db.execute(
        select(ReferralReward.milestone, ReferralReward.reward_type).where(
            ReferralReward.referrer_user_id == user_id,
            ReferralReward.status == RewardStatus.CREDITED,
        )
    ).all()
    return {(int(r[0]), r[1]) for r in rows}


def referral_summary(db: Session, referral: Referral, include_progress: bool = True) -> Dict:
    progress = db.execute(
        select(ReferralProgress).where(ReferralProgress.referral_id == referral.id)
    ).scalar_one_or_none()
    ads = progress.eligible_ads_watched if progress else 0
    referred = (
        db.execute(select(User).where(User.id == referral.referred_user_id)).scalar_one_or_none()
        if referral.referred_user_id
        else None
    )
    final = milestone_service.final_milestone(db)
    data = {
        "id": referral.id,
        "status": referral.status,
        "referredUser": mask_email(referred.email) if referred else None,
        "createdAt": referral.created_at,
        "completedAt": referral.completed_at,
        "adsWatched": ads,
        "adsRequired": final,
    }
    if include_progress:
        data["milestones"] = milestone_service.milestone_view(db, ads, _credited_keys(db, referral.id))
    return data


def next_milestone_view(db: Session, referrals: List[Referral]) -> Dict:
    """Progress card: the referral closest to its next milestone."""
    best = None
    for referral in referrals:
        if referral.status in ReferralStatus.BLOCKED:
            continue
        progress = db.execute(
            select(ReferralProgress).where(ReferralProgress.referral_id == referral.id)
        ).scalar_one_or_none()
        ads = progress.eligible_ads_watched if progress else 0
        upcoming = [m for m in milestone_service.active_milestones(db) if m.milestone > ads]
        if not upcoming:
            continue
        target = min(upcoming, key=lambda m: m.milestone)
        remaining = target.milestone - ads
        if best is None or remaining < best["adsRemaining"]:
            best = {
                "referralId": referral.id,
                "referredUser": referral_summary(db, referral, include_progress=False)["referredUser"],
                "adsWatched": ads,
                "adsRequired": target.milestone,
                "percent": min(100, round(ads * 100 / target.milestone)) if target.milestone else 100,
                "adsRemaining": remaining,
                "nextReward": {
                    "label": target.label,
                    "rewardType": target.reward_type,
                    "rewardAmount": target.reward_amount,
                    "milestone": target.milestone,
                },
            }
    return best or {
        "referralId": None,
        "referredUser": None,
        "adsWatched": 0,
        "adsRequired": milestone_service.final_milestone(db),
        "percent": 0,
        "adsRemaining": milestone_service.final_milestone(db),
        "nextReward": None,
    }


def dashboard(db: Session, user: User) -> Dict:
    stats = statistics(db, user.id)
    totals = reward_service.totals_by_type(db, user.id)
    referrals = (
        db.execute(
            select(Referral)
            .where(Referral.referrer_user_id == user.id)
            .order_by(Referral.created_at.desc())
        )
        .scalars()
        .all()
    )
    recent = [referral_summary(db, r, include_progress=False) for r in referrals[:5]]

    best_ads = 0
    if referrals:
        best_ads = int(
            db.execute(
                select(func.coalesce(func.max(ReferralProgress.eligible_ads_watched), 0)).where(
                    ReferralProgress.referral_id.in_([r.id for r in referrals])
                )
            ).scalar_one()
        )

    return {
        "referralCode": user.referral_code,
        "referralLink": referral_link(user.referral_code),
        **stats,
        "totalSvesEarned": totals.get(RewardType.SVE, 0),
        "totalXpEarned": totals.get(RewardType.XP, 0),
        "totalGemsEarned": totals.get(RewardType.GEMS, 0),
        "totalTokensEarned": totals.get(RewardType.TOKENS, 0),
        "totalSpinsEarned": totals.get(RewardType.SPINS, 0),
        "referralProgress": next_milestone_view(db, referrals),
        "rewardMilestones": milestone_service.milestone_view(
            db,
            ads_watched=best_ads,
            credited_keys=credited_keys_for_referrer(db, user.id),
        ),
        "recentReferrals": recent,
        "balances": {
            "sve": user.sve_balance,
            "tokens": user.token_balance,
            "gems": user.gem_balance,
            "spins": user.spin_balance,
            "xp": user.xp,
            "level": user.level,
        },
    }


def list_referrals(
    db: Session, user_id: str, page: int = 1, limit: int = 20, status: Optional[str] = None
) -> Dict:
    filters = [Referral.referrer_user_id == user_id]
    if status:
        status = status.upper()
        mapping = {
            "SUCCESSFUL": [ReferralStatus.SUCCESSFUL],
            "PENDING": [ReferralStatus.PENDING, ReferralStatus.QUALIFYING],
            "SPAM": [ReferralStatus.SPAM, ReferralStatus.REJECTED, ReferralStatus.FRAUD_REVIEW],
        }
        if status != "ALL":
            if status not in mapping:
                raise AppError(ErrorCode.VALIDATION_ERROR, "Unsupported status filter.", 422)
            filters.append(Referral.status.in_(mapping[status]))

    total = int(db.execute(select(func.count(Referral.id)).where(*filters)).scalar_one())
    rows = (
        db.execute(
            select(Referral)
            .where(*filters)
            .order_by(Referral.created_at.desc())
            .limit(limit)
            .offset((page - 1) * limit)
        )
        .scalars()
        .all()
    )
    return {
        "items": [referral_summary(db, r, include_progress=False) for r in rows],
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": (total + limit - 1) // limit,
    }


def spam_summary(db: Session, user_id: str, limit: int = 10) -> Dict:
    count = int(
        db.execute(
            select(func.count(SpamReferral.id)).where(SpamReferral.referrer_user_id == user_id)
        ).scalar_one()
    )
    rows = (
        db.execute(
            select(SpamReferral)
            .where(SpamReferral.referrer_user_id == user_id)
            .order_by(SpamReferral.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    # Only non-sensitive fields are exposed - no device hash, IP or risk score.
    return {
        "spamCount": count,
        "recentSpam": [
            {
                "id": r.id,
                "createdAt": r.created_at,
                "status": "NOT_ELIGIBLE",
                "message": "This referral attempt was not eligible for rewards.",
            }
            for r in rows
        ],
    }


def progress_detail(db: Session, user: User, referral_id: str) -> Dict:
    referral = db.execute(select(Referral).where(Referral.id == referral_id)).scalar_one_or_none()
    if referral is None:
        raise AppError(ErrorCode.NOT_FOUND, "Referral not found.", 404)
    if referral.referrer_user_id != user.id and user.role != "admin":
        # Ownership check (spec 68) - IDOR protection.
        raise AppError(ErrorCode.FORBIDDEN, "You do not have access to this referral.", 403)

    summary = referral_summary(db, referral)
    milestones = summary["milestones"]
    summary["milestonesReached"] = [m for m in milestones if m["unlocked"]]
    summary["milestonesRemaining"] = [m for m in milestones if not m["unlocked"]]
    summary["updatedAt"] = utcnow()
    return summary
