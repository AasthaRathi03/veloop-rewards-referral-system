"""Password hashing, JWT access tokens, device tokens and HMAC hashing."""
import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AppError, ErrorCode


# ------------------------- passwords -------------------------
def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ------------------------- access tokens -------------------------
def create_access_token(user_id: str, role: str = "user") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise AppError(ErrorCode.UNAUTHORIZED, "Invalid or expired session.", 401)
    if payload.get("typ") != "access":
        raise AppError(ErrorCode.UNAUTHORIZED, "Invalid session token.", 401)
    return payload


# ------------------------- HMAC hashing -------------------------
def _hmac(secret: str, value: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def hash_device_signals(normalized_signals: str) -> str:
    """Server-side HMAC of normalized device signals. Raw fingerprints are never stored."""
    return _hmac(settings.DEVICE_HASH_SECRET, normalized_signals)


def hash_ip(ip: str) -> str:
    """IP is stored only as a peppered hash (privacy requirement #37)."""
    if not ip:
        return ""
    return _hmac(settings.IP_HASH_SECRET, ip)


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")


# ------------------------- device tokens -------------------------
def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def issue_device_token(device_id: str, device_hash: str, version: int = 1) -> str:
    """Signed, tamper-resistant, rotatable, revocable device token (payload.signature)."""
    payload = {
        "did": device_id,
        "dh": device_hash[:32],
        "v": version,
        "jti": secrets.token_urlsafe(8),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(days=settings.DEVICE_TOKEN_EXPIRE_DAYS)).timestamp()),
    }
    raw = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = _hmac(settings.DEVICE_TOKEN_SECRET, raw)
    return f"{raw}.{sig}"


def verify_device_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Returns payload if the signature is valid and unexpired, else None (never raises)."""
    if not token or "." not in token:
        return None
    raw, _, sig = token.partition(".")
    if not constant_time_equals(_hmac(settings.DEVICE_TOKEN_SECRET, raw), sig):
        return None
    try:
        payload = json.loads(_b64d(raw))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        return None
    return payload


def verify_provider_signature(payload: str, signature: str) -> bool:
    """HMAC verification for ad-provider server-to-server postbacks."""
    return constant_time_equals(_hmac(settings.AD_PROVIDER_SECRET, payload), signature)
