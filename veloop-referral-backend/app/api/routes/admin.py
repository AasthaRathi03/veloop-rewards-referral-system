"""Admin/support visibility (spec 90) - backing data for a future admin panel."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.errors import AppError, ErrorCode
from app.db.base import get_db, utcnow
from app.models import (
    AuditAction,
    AuditLog,
    Referral,
    ReferralProgress,
    ReferralReward,
    ReferralStatus,
    SpamReferral,
    User,
)
from app.schemas.common import ok
from app.schemas.referral import AdminStatusIn
from app.services import audit_service, milestone_service, reward_service

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/referrals")
def all_referrals(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, max_length=20),
    db: Session = Depends(get_db),
):
    filters = []
    if status:
        filters.append(Referral.status == status.upper())
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
    return ok(
        {
            "items": [
                {
                    "id": r.id,
                    "referrerUserId": r.referrer_user_id,
                    "referredUserId": r.referred_user_id,
                    "status": r.status,
                    "riskScore": r.risk_score,
                    "riskLevel": r.risk_level,
                    "createdAt": r.created_at,
                    "completedAt": r.completed_at,
                }
                for r in rows
            ],
            "page": page,
            "limit": limit,
        }
    )


@router.get("/referrals/{referral_id}")
def referral_detail(referral_id: str, db: Session = Depends(get_db)):
    referral = db.execute(select(Referral).where(Referral.id == referral_id)).scalar_one_or_none()
    if not referral:
        raise AppError(ErrorCode.NOT_FOUND, "Referral not found.", 404)
    progress = db.execute(
        select(ReferralProgress).where(ReferralProgress.referral_id == referral_id)
    ).scalar_one_or_none()
    rewards = (
        db.execute(select(ReferralReward).where(ReferralReward.referral_id == referral_id))
        .scalars()
        .all()
    )
    spam = (
        db.execute(select(SpamReferral).where(SpamReferral.referral_id == referral_id)).scalars().all()
    )
    logs = (
        db.execute(
            select(AuditLog)
            .where(AuditLog.entity_id == referral_id)
            .order_by(AuditLog.created_at.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )
    return ok(
        {
            "referral": {
                "id": referral.id,
                "referrerUserId": referral.referrer_user_id,
                "referredUserId": referral.referred_user_id,
                "status": referral.status,
                "riskScore": referral.risk_score,
                "riskLevel": referral.risk_level,
                "deviceId": referral.device_id,
                "createdAt": referral.created_at,
                "completedAt": referral.completed_at,
            },
            "adProgress": progress.eligible_ads_watched if progress else 0,
            "rewards": [
                {
                    "milestone": r.milestone,
                    "rewardType": r.reward_type,
                    "amount": r.reward_amount,
                    "status": r.status,
                    "creditedAt": r.credited_at,
                }
                for r in rewards
            ],
            "fraudFlags": [
                {
                    "reason": s.reason,
                    "detail": s.reason_detail,
                    "category": s.risk_category,
                    "riskScore": s.risk_score,
                    "createdAt": s.created_at,
                }
                for s in spam
            ],
            "auditTrail": [
                {
                    "action": l.action,
                    "meta": json.loads(l.meta) if l.meta else None,
                    "createdAt": l.created_at,
                }
                for l in logs
            ],
        }
    )


@router.patch("/referrals/{referral_id}/status")
def change_status(
    referral_id: str,
    payload: AdminStatusIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """The only authorized way to mutate an attributed referral."""
    referral = db.execute(select(Referral).where(Referral.id == referral_id)).scalar_one_or_none()
    if not referral:
        raise AppError(ErrorCode.NOT_FOUND, "Referral not found.", 404)
    new_status = payload.status.upper()
    valid = set(ReferralStatus.ACTIVE) | set(ReferralStatus.BLOCKED) | {ReferralStatus.LINK_CLICKED}
    if new_status not in valid:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Unsupported status.", 422)

    previous, referral.status = referral.status, new_status
    if new_status == ReferralStatus.SUCCESSFUL and not referral.completed_at:
        referral.completed_at = utcnow()
    audit_service.log(
        db, AuditAction.ADMIN_STATUS_CHANGE, "referral", referral.id,
        actor_user_id=admin.id, meta={"from": previous, "to": new_status, "reason": payload.reason},
    )
    if new_status in ReferralStatus.ACTIVE:
        milestone_service.evaluate(db, referral)
    db.commit()
    return ok({"id": referral.id, "status": referral.status})


@router.get("/reconciliation/{user_id}")
def reconciliation(user_id: str, db: Session = Depends(get_db)):
    """Ledger totals vs stored balances (spec 103)."""
    return ok(reward_service.reconcile(db, user_id))


@router.get("/audit")
def audit(
    action: Optional[str] = Query(None, max_length=48),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    filters = [AuditLog.action == action] if action else []
    rows = (
        db.execute(
            select(AuditLog).where(*filters).order_by(AuditLog.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    return ok(
        [
            {
                "action": l.action,
                "entityType": l.entity_type,
                "entityId": l.entity_id,
                "actorUserId": l.actor_user_id,
                "meta": json.loads(l.meta) if l.meta else None,
                "createdAt": l.created_at,
            }
            for l in rows
        ]
    )
