"""Reward ledger.

A balance is NEVER modified outside this module, and never without a
RewardTransaction row. Every credit is idempotent on `idempotency_key`.
"""
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utcnow
from app.models import AuditAction, RewardStatus, RewardTransaction, User
from app.services import audit_service

XP_PER_LEVEL = 500


def _lock_user(db: Session, user_id: str) -> User:
    stmt = select(User).where(User.id == user_id)
    if not settings.is_sqlite:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one()


def credit(
    db: Session,
    user_id: str,
    reward_type: str,
    amount: int,
    reason: str,
    idempotency_key: str,
    referral_id: Optional[str] = None,
    reward_id: Optional[str] = None,
    milestone: Optional[int] = None,
    source: str = "REFERRAL",
) -> Tuple[RewardTransaction, bool]:
    """Credit a reward exactly once.

    Returns (transaction, created). `created=False` means the same logical
    reward had already been issued - the caller must not credit again.
    """
    existing = db.execute(
        select(RewardTransaction).where(RewardTransaction.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing:
        return existing, False

    user = _lock_user(db, user_id)
    field = User.BALANCE_FIELD[reward_type]
    new_balance = getattr(user, field) + amount

    txn = RewardTransaction(
        user_id=user_id,
        referral_id=referral_id,
        reward_id=reward_id,
        reward_type=reward_type,
        amount=amount,
        reason=reason,
        milestone=milestone,
        source=source,
        status=RewardStatus.CREDITED,
        balance_after=new_balance,
        idempotency_key=idempotency_key,
    )
    db.add(txn)
    try:
        db.flush()
    except IntegrityError:
        # Lost the race against a concurrent identical credit - honour the winner.
        db.rollback()
        existing = db.execute(
            select(RewardTransaction).where(RewardTransaction.idempotency_key == idempotency_key)
        ).scalar_one()
        return existing, False

    setattr(user, field, new_balance)
    if reward_type == "XP":
        user.level = max(1, new_balance // XP_PER_LEVEL + 1)
    db.flush()

    audit_service.log(
        db,
        AuditAction.REWARD_CREDITED,
        "reward_transaction",
        txn.id,
        actor_user_id=user_id,
        meta={
            "rewardType": reward_type,
            "amount": amount,
            "milestone": milestone,
            "referralId": referral_id,
            "balanceAfter": new_balance,
        },
    )
    return txn, True


def totals_by_type(db: Session, user_id: str, source: str = "REFERRAL") -> dict:
    """Referral earnings come from the ledger - never from client state."""
    from sqlalchemy import func

    rows = db.execute(
        select(RewardTransaction.reward_type, func.coalesce(func.sum(RewardTransaction.amount), 0))
        .where(
            RewardTransaction.user_id == user_id,
            RewardTransaction.source == source,
            RewardTransaction.status == RewardStatus.CREDITED,
        )
        .group_by(RewardTransaction.reward_type)
    ).all()
    return {r[0]: int(r[1]) for r in rows}


def history(db: Session, user_id: str, limit: int = 50, offset: int = 0):
    return (
        db.execute(
            select(RewardTransaction)
            .where(RewardTransaction.user_id == user_id, RewardTransaction.source == "REFERRAL")
            .order_by(RewardTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )


def reconcile(db: Session, user_id: str) -> dict:
    """Ledger total vs stored balance - mismatches must be detectable (spec 103)."""
    from sqlalchemy import func

    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
    rows = db.execute(
        select(RewardTransaction.reward_type, func.coalesce(func.sum(RewardTransaction.amount), 0))
        .where(
            RewardTransaction.user_id == user_id,
            RewardTransaction.status == RewardStatus.CREDITED,
        )
        .group_by(RewardTransaction.reward_type)
    ).all()
    ledger = {r[0]: int(r[1]) for r in rows}
    report = {}
    for reward_type, field in User.BALANCE_FIELD.items():
        expected = ledger.get(reward_type, 0)
        actual = getattr(user, field)
        report[reward_type] = {
            "ledger": expected,
            "balance": actual,
            "match": expected == actual,
        }
    report["checkedAt"] = utcnow().isoformat()
    return report
