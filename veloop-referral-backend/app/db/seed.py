"""Seed the milestone configuration (reward rules live in the database)."""
from sqlalchemy import select

from app.db.base import SessionLocal
from app.models import MilestoneConfig, RewardType

DEFAULT_MILESTONES = [
    dict(milestone=15, reward_type=RewardType.SVE, reward_amount=5000, label="5,000 SVE",
         subtitle="≈ ₹10", condition_text="Friend completes 15 Ad Watch tasks", sort_order=1),
    dict(milestone=20, reward_type=RewardType.SPINS, reward_amount=2, label="2 Lucky Spins",
         subtitle=None, condition_text="Friend completes 20 Ad Watch tasks", sort_order=2),
    dict(milestone=30, reward_type=RewardType.TOKENS, reward_amount=5000, label="5,000 Tokens",
         subtitle=None, condition_text="Friend completes 30 Ad Watch tasks", sort_order=3),
    dict(milestone=35, reward_type=RewardType.GEMS, reward_amount=10, label="10 Gems",
         subtitle=None, condition_text="Friend completes 35 Ad Watch tasks", sort_order=4),
    dict(milestone=0, reward_type=RewardType.XP, reward_amount=20, label="+20 XP",
         subtitle=None, condition_text="Awarded for every successful referral", sort_order=0),
]


def seed_milestones(session=None) -> None:
    own = session is None
    db = session or SessionLocal()
    try:
        for cfg in DEFAULT_MILESTONES:
            exists = db.execute(
                select(MilestoneConfig).where(
                    MilestoneConfig.milestone == cfg["milestone"],
                    MilestoneConfig.reward_type == cfg["reward_type"],
                )
            ).scalar_one_or_none()
            if not exists:
                db.add(MilestoneConfig(**cfg))
        db.commit()
    finally:
        if own:
            db.close()
