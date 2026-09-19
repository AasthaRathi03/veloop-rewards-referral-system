"""Ad completion intake - the only way referral progress can move."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_device
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.rate_limit import RateLimit
from app.core.security import verify_provider_signature
from app.db.base import get_db
from app.models import User
from app.schemas.ads import AdCompleteIn, AdPostbackIn
from app.schemas.common import ok
from app.services import ad_service
from app.services.device_service import ResolvedDevice
from app.utils.idempotency import get_stored_response, store_response

router = APIRouter(prefix="/ads", tags=["ads"])


@router.post(
    "/complete",
    dependencies=[Depends(RateLimit(settings.RATE_LIMIT_AD_EVENT, "ad", by_user=True))],
)
def complete_ad(
    payload: AdCompleteIn,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device: ResolvedDevice = Depends(get_device),
):
    """Called by the referred user's client after an ad finishes.

    The payload never contains a reward or a counter - only an event id, which
    the backend validates and de-duplicates.
    """
    cached = get_stored_response(db, "ads.complete", user.id, idempotency_key)
    if cached:
        return cached

    result = ad_service.record_completion(
        db,
        user=user,
        provider=payload.provider,
        provider_event_id=payload.providerEventId,
        watched_seconds=payload.watchedSeconds,
        ad_unit=payload.adUnit,
        completed_at=payload.completedAt,
        device_hash=device.device_hash,
        ip_hash=device.ip_hash,
    )
    body = ok(result)
    store_response(db, "ads.complete", user.id, idempotency_key, body)
    db.commit()
    return body


@router.post("/postback")
async def provider_postback(
    request: Request,
    x_veloop_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Server-to-server postback. Requires a valid HMAC over the raw body."""
    raw = (await request.body()).decode()
    if not x_veloop_signature or not verify_provider_signature(raw, x_veloop_signature):
        raise AppError(ErrorCode.AD_EVENT_REJECTED, "Invalid provider signature.", 401)

    payload = AdPostbackIn(**json.loads(raw))
    user = db.execute(select(User).where(User.id == payload.userId)).scalar_one_or_none()
    if user is None:
        raise AppError(ErrorCode.AD_EVENT_REJECTED, "Unknown user.", 400)

    result = ad_service.record_completion(
        db,
        user=user,
        provider=payload.provider,
        provider_event_id=payload.providerEventId,
        watched_seconds=payload.watchedSeconds,
        ad_unit=payload.adUnit,
        completed_at=payload.completedAt,
    )
    db.commit()
    return ok(result)
