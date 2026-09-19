"""Referral code generation - server side only, never accepted from the client."""
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars (0/O, 1/I)
PREFIX = "VELOOP"


def generate_referral_code(db: Session, length: int = 5, max_attempts: int = 20) -> str:
    from app.models import User

    for _ in range(max_attempts):
        code = PREFIX + "".join(secrets.choice(ALPHABET) for _ in range(length))
        exists = db.execute(select(User.id).where(User.referral_code == code)).first()
        if not exists:
            return code
    raise RuntimeError("Could not generate a unique referral code")  # pragma: no cover


def normalize_code(code: str) -> str:
    return (code or "").strip().upper()
