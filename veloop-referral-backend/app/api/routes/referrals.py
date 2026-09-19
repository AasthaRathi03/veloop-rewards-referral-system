"""Referral endpoints. Every value the frontend renders originates here."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_device, parse_device_signals
from app.core.config import settings
from app.core.rate_limit import RateLimit
from app.db.base import get_db
from app.models import User
from app.schemas.common import ok
from app.schemas.referral import AttributeIn, ClickIn
from app.services import milestone_service, referral_service, reward_service
from app.services.device_service import ResolvedDevice

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.get("/me", dependencies=[Depends(RateLimit(settings.RATE_LIMIT_READ, "read", by_user=True))])
def my_referral_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Single call that powers the whole referral page."""
    return ok(referral_service.dashboard(db, user))


@router.post(
    "/attribute",
    dependencies=[Depends(RateLimit(settings.RATE_LIMIT_ATTRIBUTE, "attribute"))],
)
def attribute_referral(
    payload: AttributeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device: ResolvedDevice = Depends(get_device),
):
    """Attach a referrer to the *authenticated* user. Immutable once set."""
    referral = referral_service.attribute(db, user, payload.referralCode, device, source=payload.source)
    db.commit()
    return ok({"referralId": referral.id, "status": referral.status})


@router.post("/click", dependencies=[Depends(RateLimit("30/60", "click"))])
def track_click(payload: ClickIn, request: Request, db: Session = Depends(get_db)):
    """Public: records a link click (never a referral)."""
    signals = parse_device_signals(request)
    from app.core.security import hash_device_signals, hash_ip

    click_id = referral_service.track_click(
        db,
        payload.referralCode,
        device_hash=hash_device_signals(signals.normalized()),
        ip_hash=hash_ip(signals.ip),
        ua_family=signals.ua_family(),
    )
    db.commit()
    return ok({"clickId": click_id})


@router.get("", dependencies=[Depends(RateLimit(settings.RATE_LIMIT_READ, "read", by_user=True))])
def list_referrals(
    page: int = Query(1, ge=1, le=10_000),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, max_length=16, pattern=r"^[A-Za-z]+$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(referral_service.list_referrals(db, user.id, page=page, limit=limit, status=status))


@router.get("/spam", dependencies=[Depends(RateLimit(settings.RATE_LIMIT_READ, "read", by_user=True))])
def spam_referrals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(referral_service.spam_summary(db, user.id))


@router.get("/rewards/history")
def reward_history(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = reward_service.history(db, user.id, limit=limit, offset=(page - 1) * limit)
    return ok(
        {
            "items": [
                {
                    "id": t.id,
                    "rewardType": t.reward_type,
                    "amount": t.amount,
                    "reason": t.reason,
                    "milestone": t.milestone,
                    "referralId": t.referral_id,
                    "createdAt": t.created_at,
                    "status": t.status,
                }
                for t in rows
            ],
            "page": page,
            "limit": limit,
        }
    )


@router.get("/config/milestones", dependencies=[Depends(RateLimit(settings.RATE_LIMIT_READ, "read"))])
def milestone_config(db: Session = Depends(get_db)):
    """Public program configuration - reward structure lives in the DB, not in React."""
    return ok({"milestones": milestone_service.milestone_view(db, 0, set())})


@router.get("/{referral_id}/progress")
def referral_progress(
    referral_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return ok(referral_service.progress_detail(db, user, referral_id))
