"""Layered fraud / self-referral detection.

Design rules from the spec:
  * never decide on a single weak signal (an IP match alone is not fraud);
  * combine device, account, network, graph, history and behavioural signals;
  * high confidence -> reject, ambiguous -> FRAUD_REVIEW, clean -> PENDING;
  * the score and reasons are internal and never returned to normal users.
"""
from dataclasses import dataclass, field
from datetime import timedelta
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utcnow
from app.models import (
    AuditAction,
    Device,
    Referral,
    ReferralStatus,
    RiskLevel,
    SpamReferral,
    User,
    UserDevice,
)
from app.services import audit_service, device_service


@dataclass
class RiskAssessment:
    score: int = 0
    reasons: List[str] = field(default_factory=list)
    self_referral: bool = False
    matched_account_id: Optional[str] = None

    @property
    def level(self) -> str:
        if self.score >= settings.RISK_HIGH_THRESHOLD:
            return RiskLevel.HIGH
        if self.score >= settings.RISK_REVIEW_THRESHOLD:
            return RiskLevel.REVIEW
        return RiskLevel.LOW

    def add(self, points: int, reason: str) -> None:
        self.score = min(100, self.score + points)
        self.reasons.append(reason)


# Signal weights - configurable in one place.
W_DEVICE_BELONGS_TO_REFERRER = 70   # the referrer already used THIS device
W_DEVICE_HAS_OTHER_ACCOUNTS = 25    # multi-accounting on one device
W_DEVICE_BLOCKED = 80
W_TOKEN_MISMATCH = 10               # device token vs fingerprint drift
W_IP_MATCH = 12                     # weak on its own (shared wifi/CGNAT)
W_EMAIL_SIMILAR = 20
W_PHONE_MATCH = 35
W_FRESH_REFERRER_BURST = 18         # many referrals from same device recently
W_REFERRER_SPAM_HISTORY = 12
W_NEW_ACCOUNT_BURST = 10


def _email_root(email: str) -> str:
    """Gmail-style normalization: dots + '+tag' removed."""
    local, _, domain = (email or "").lower().partition("@")
    local = local.split("+")[0].replace(".", "")
    return f"{local}@{domain}"


def _email_similarity(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if _email_root(a) == _email_root(b):
        return True
    la, lb = a.split("@")[0].lower(), b.split("@")[0].lower()
    if len(la) >= 5 and len(lb) >= 5 and (la.startswith(lb[:5]) or lb.startswith(la[:5])):
        return a.split("@")[-1] == b.split("@")[-1]
    return False


def assess_referral_risk(
    db: Session,
    referrer: User,
    device: Device,
    ip_hash: str,
    candidate_email: str,
    candidate_phone: Optional[str] = None,
    candidate_user: Optional[User] = None,
    token_mismatch: bool = False,
) -> RiskAssessment:
    """Score a referral attribution attempt."""
    risk = RiskAssessment()

    # 1. Hard self-referral: same account.
    if candidate_user is not None and candidate_user.id == referrer.id:
        risk.add(100, "SAME_ACCOUNT")
        risk.self_referral = True
        risk.matched_account_id = referrer.id
        return risk

    # 2. Device already associated with the referrer's own account.
    device_accounts = device_service.accounts_on_device(db, device.id)
    if referrer.id in device_accounts:
        risk.add(W_DEVICE_BELONGS_TO_REFERRER, "DEVICE_BELONGS_TO_REFERRER")
        risk.self_referral = True
        risk.matched_account_id = referrer.id

    # 3. Device already has other accounts (multi-accounting).
    other_accounts = [a for a in device_accounts if not (candidate_user and a == candidate_user.id)]
    if other_accounts and referrer.id not in device_accounts:
        risk.add(W_DEVICE_HAS_OTHER_ACCOUNTS, "DEVICE_HAS_EXISTING_ACCOUNTS")
        risk.matched_account_id = risk.matched_account_id or other_accounts[0]

    if device.blocked:
        risk.add(W_DEVICE_BLOCKED, "DEVICE_BLOCKED")

    if token_mismatch:
        risk.add(W_TOKEN_MISMATCH, "DEVICE_TOKEN_FINGERPRINT_DRIFT")

    # 4. Network signal - weak, only contributes with others.
    referrer_devices = device_service.devices_of_user(db, referrer.id)
    if ip_hash and referrer_devices:
        ip_match = db.execute(
            select(func.count(Device.id)).where(
                Device.id.in_(referrer_devices),
                Device.last_ip_hash == ip_hash,
            )
        ).scalar_one()
        if ip_match:
            risk.add(W_IP_MATCH, "SHARED_NETWORK")

    # 5. Identity relationships.
    if _email_similarity(referrer.email, candidate_email):
        risk.add(W_EMAIL_SIMILAR, "SIMILAR_EMAIL")
    if candidate_phone and referrer.phone and candidate_phone == referrer.phone:
        risk.add(W_PHONE_MATCH, "SAME_PHONE")

    # 6. Behaviour: referral burst from the same device in the last 24h.
    since = utcnow() - timedelta(hours=24)
    burst = db.execute(
        select(func.count(Referral.id)).where(
            Referral.device_id == device.id, Referral.created_at >= since
        )
    ).scalar_one()
    if burst >= 2:
        risk.add(W_FRESH_REFERRER_BURST, "REFERRAL_BURST_SAME_DEVICE")

    # 7. Referrer abuse history.
    spam_history = db.execute(
        select(func.count(SpamReferral.id)).where(SpamReferral.referrer_user_id == referrer.id)
    ).scalar_one()
    if spam_history >= 3:
        risk.add(W_REFERRER_SPAM_HISTORY, "REFERRER_SPAM_HISTORY")

    # 8. Account age of the referrer (very fresh accounts referring instantly).
    if referrer.created_at and (utcnow() - referrer.created_at.replace(tzinfo=utcnow().tzinfo)) < timedelta(minutes=5):
        risk.add(W_NEW_ACCOUNT_BURST, "REFERRER_ACCOUNT_VERY_NEW")

    # Self-referral is only asserted with layered evidence, never one weak signal.
    if not risk.self_referral:
        strong = {"DEVICE_BELONGS_TO_REFERRER", "SAME_PHONE"}
        combo = {"DEVICE_HAS_EXISTING_ACCOUNTS", "SIMILAR_EMAIL", "SHARED_NETWORK"}
        if strong & set(risk.reasons) or len(combo & set(risk.reasons)) >= 2:
            risk.self_referral = risk.score >= settings.RISK_HIGH_THRESHOLD

    return risk


def status_for_risk(risk: RiskAssessment) -> str:
    if risk.level == RiskLevel.HIGH:
        return ReferralStatus.SPAM
    if risk.level == RiskLevel.REVIEW:
        return ReferralStatus.FRAUD_REVIEW
    return ReferralStatus.PENDING


def record_spam(
    db: Session,
    referrer_user_id: str,
    risk: RiskAssessment,
    referral_id: Optional[str] = None,
    referred_user_id: Optional[str] = None,
    device_hash: Optional[str] = None,
    ip_hash: Optional[str] = None,
    status: str = "BLOCKED",
) -> SpamReferral:
    record = SpamReferral(
        referral_id=referral_id,
        referrer_user_id=referrer_user_id,
        referred_user_id=referred_user_id,
        reason=risk.reasons[0] if risk.reasons else "SUSPICIOUS",
        reason_detail=",".join(risk.reasons),
        risk_category="SELF_REFERRAL" if risk.self_referral else "REFERRAL_ABUSE",
        device_hash=device_hash,
        ip_hash=ip_hash,
        risk_score=risk.score,
        status=status,
    )
    db.add(record)
    db.flush()
    audit_service.log(
        db,
        AuditAction.REFERRAL_MARKED_SPAM,
        "referral",
        referral_id,
        actor_user_id=referred_user_id,
        meta={"riskScore": risk.score, "reasons": risk.reasons, "level": risk.level},
        ip_hash=ip_hash,
    )
    return record


def find_existing_account_on_device(db: Session, device: Device) -> Optional[User]:
    row = db.execute(
        select(User)
        .join(UserDevice, UserDevice.user_id == User.id)
        .where(UserDevice.device_id == device.id)
        .order_by(UserDevice.created_at.asc())
    ).scalars().first()
    return row
