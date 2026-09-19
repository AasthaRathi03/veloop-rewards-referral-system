"""Seed milestone config + an optional demo dataset.

    python -m scripts.seed_demo            # milestone config only
    python -m scripts.seed_demo --demo     # + demo referrer/referred users & ad events
"""
import argparse
import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import Base, SessionLocal, engine
from app.db.seed import seed_milestones
from app.models import AdEvent, User
from app.services import ad_service
from app.services.device_service import DeviceSignals, resolve_device
from app.services.referral_service import attribute
from app.utils.codes import generate_referral_code


def create_user(db, email, device_id):
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        return user
    user = User(email=email, password_hash=hash_password("Password123!"),
                referral_code=generate_referral_code(db))
    db.add(user)
    db.flush()
    return user


def main(demo: bool) -> None:
    Base.metadata.create_all(engine)
    seed_milestones()
    if not demo:
        print("Milestone configuration seeded.")
        return

    db = SessionLocal()
    try:
        referrer = create_user(db, "demo.referrer@veloop.test", "demo-device-1")
        db.commit()
        print(f"Referrer: {referrer.email} / Password123!  code={referrer.referral_code}")

        for i, ads in enumerate([35, 18, 6], start=1):
            friend = create_user(db, f"demo.friend{i}@veloop.test", f"demo-device-{i+1}")
            db.commit()
            device = resolve_device(db, DeviceSignals(platform=f"demo-{i}", screen="1080x1920x24",
                                                      timezone="Asia/Kolkata", language="en",
                                                      hardware=f"demo-hw-{i}", canvas_hint=f"c{i}"))
            try:
                attribute(db, friend, referrer.referral_code, device, source="SEED")
                db.commit()
            except Exception as exc:  # already attributed
                db.rollback()
                print("  attribution skipped:", exc)
            for _ in range(ads):
                db.add(AdEvent(user_id=friend.id, provider="seed",
                               provider_event_id=str(uuid.uuid4()), watched_seconds=30, eligible=True))
            db.commit()
            ad_service.sync_referral_progress(db, friend.id)
            db.commit()
            print(f"  friend{i}: {ads} ads")
        db.refresh(referrer)
        print(f"Balances -> SVE {referrer.sve_balance}, tokens {referrer.token_balance}, "
              f"gems {referrer.gem_balance}, spins {referrer.spin_balance}, xp {referrer.xp}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="create demo users and ad events")
    main(parser.parse_args().demo)
