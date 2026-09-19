"""Authentication + registration (with referral attribution at signup)."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_device
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.rate_limit import RateLimit
from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import get_db
from app.models import AuditAction, User
from app.schemas.auth import AuthOut, LoginIn, RegisterIn
from app.schemas.common import ok
from app.services import audit_service, device_service, referral_service
from app.services.device_service import ResolvedDevice
from app.utils.codes import generate_referral_code

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_KWARGS = dict(
    httponly=True,
    secure=settings.ENV != "development",
    samesite="lax",
    max_age=settings.DEVICE_TOKEN_EXPIRE_DAYS * 86400,
)


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "referralCode": user.referral_code,
        "level": user.level,
        "balances": {
            "sve": user.sve_balance,
            "tokens": user.token_balance,
            "gems": user.gem_balance,
            "spins": user.spin_balance,
            "xp": user.xp,
        },
    }


@router.post("/register", response_model=None, dependencies=[Depends(RateLimit(settings.RATE_LIMIT_AUTH, "auth"))])
def register(
    payload: RegisterIn,
    response: Response,
    db: Session = Depends(get_db),
    device: ResolvedDevice = Depends(get_device),
):
    existing = db.execute(select(User).where(User.email == str(payload.email).lower())).scalar_one_or_none()
    if existing:
        raise AppError(ErrorCode.EMAIL_ALREADY_REGISTERED, "An account with this email already exists.", 409)

    precomputed = None
    if payload.referralCode:
        # Blocks obvious self-referral BEFORE creating the account (spec 34).
        precomputed = referral_service.guard_pre_registration(
            db, payload.referralCode, device, str(payload.email), payload.phone
        )

    user = User(
        email=str(payload.email).lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        referral_code=generate_referral_code(db),
    )
    db.add(user)
    db.flush()
    device_service.link_user_device(db, user.id, device.device, device.ip_hash)
    audit_service.log(
        db, AuditAction.USER_REGISTERED, "user", user.id, actor_user_id=user.id, ip_hash=device.ip_hash
    )

    referral_info = None
    if payload.referralCode:
        referral = referral_service.attribute(
            db, user, payload.referralCode, device, source="REGISTRATION", precomputed=precomputed
        )
        referral_info = {"status": referral.status, "referralId": referral.id}

    db.commit()
    db.refresh(user)

    response.set_cookie("veloop_did", device.device_token, **COOKIE_KWARGS)
    return ok(
        AuthOut(
            accessToken=create_access_token(user.id, user.role),
            deviceToken=device.device_token,
            user=_user_payload(user),
            referral=referral_info,
        ).model_dump()
    )


@router.post("/login", dependencies=[Depends(RateLimit(settings.RATE_LIMIT_AUTH, "auth"))])
def login(
    payload: LoginIn,
    response: Response,
    db: Session = Depends(get_db),
    device: ResolvedDevice = Depends(get_device),
):
    user = db.execute(select(User).where(User.email == str(payload.email).lower())).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        # Same message for both cases - no account enumeration.
        raise AppError(ErrorCode.INVALID_CREDENTIALS, "Email or password is incorrect.", 401)

    device_service.link_user_device(db, user.id, device.device, device.ip_hash)
    db.commit()

    response.set_cookie("veloop_did", device.device_token, **COOKIE_KWARGS)
    return ok(
        AuthOut(
            accessToken=create_access_token(user.id, user.role),
            deviceToken=device.device_token,
            user=_user_payload(user),
        ).model_dump()
    )


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return ok(_user_payload(user))
