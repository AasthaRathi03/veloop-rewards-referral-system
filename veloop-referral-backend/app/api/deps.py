"""Shared FastAPI dependencies: authentication, device resolution, admin guard."""
import base64
import json
from typing import Optional

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.rate_limit import client_ip
from app.core.security import decode_access_token
from app.db.base import get_db
from app.models import User
from app.services.device_service import DeviceSignals, ResolvedDevice, resolve_device


def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> User:
    """Identity ALWAYS comes from the verified token - never from the request body."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(ErrorCode.UNAUTHORIZED, "Authentication required.", 401)
    payload = decode_access_token(authorization.split(" ", 1)[1].strip())
    user = db.execute(select(User).where(User.id == payload["sub"])).scalar_one_or_none()
    if user is None or user.status != "ACTIVE":
        raise AppError(ErrorCode.UNAUTHORIZED, "Session is no longer valid.", 401)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AppError(ErrorCode.FORBIDDEN, "Admin access required.", 403)
    return user


def parse_device_signals(request: Request) -> DeviceSignals:
    """Signals arrive as a base64 JSON header; headers add network/UA context."""
    raw = request.headers.get("x-device-signals")
    data = {}
    if raw:
        try:
            data = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
    return DeviceSignals(
        platform=str(data.get("platform", ""))[:64],
        screen=str(data.get("screen", ""))[:32],
        timezone=str(data.get("timezone", ""))[:64],
        language=str(data.get("language", ""))[:16],
        hardware=str(data.get("hardware", ""))[:32],
        canvas_hint=str(data.get("canvasHint", ""))[:64],
        device_token=request.headers.get("x-device-token") or request.cookies.get("veloop_did"),
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent", "")[:256],
    )


def get_device(request: Request, db: Session = Depends(get_db)) -> ResolvedDevice:
    return resolve_device(db, parse_device_signals(request))
