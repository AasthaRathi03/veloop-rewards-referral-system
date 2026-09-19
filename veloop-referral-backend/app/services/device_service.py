"""Device identity + layered device risk signals.

Raw fingerprints are never stored. Signals are normalized server-side and
reduced to an HMAC ("device hash"). A signed device token is issued so returning
browsers/incognito sessions on the same machine can still be recognised.
"""
import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_device_signals, hash_ip, issue_device_token, verify_device_token
from app.db.base import utcnow
from app.models import AuditAction, Device, UserDevice
from app.services import audit_service

_UA_FAMILY = re.compile(r"(Chrome|Firefox|Safari|Edg|OPR|SamsungBrowser|Android|iPhone|iPad)", re.I)


@dataclass
class DeviceSignals:
    """Signals collected by the frontend + request headers.

    Browser-specific values (user agent, browser name) are deliberately EXCLUDED
    from the hash so that switching Chrome -> Firefox -> Incognito on the same
    machine still resolves to the same device identity.
    """

    platform: str = ""
    screen: str = ""          # "1920x1080x24"
    timezone: str = ""
    language: str = ""
    hardware: str = ""        # "8-cores/8gb"
    canvas_hint: str = ""     # coarse, non-unique rendering hint
    device_token: Optional[str] = None
    ip: str = ""
    user_agent: str = ""
    extra: List[str] = field(default_factory=list)

    def normalized(self) -> str:
        parts = [
            self.platform.strip().lower(),
            self.screen.strip().lower(),
            self.timezone.strip().lower(),
            self.language.strip().lower()[:2],
            self.hardware.strip().lower(),
            self.canvas_hint.strip().lower()[:32],
        ]
        return "|".join(parts)

    def ua_family(self) -> str:
        m = _UA_FAMILY.search(self.user_agent or "")
        return m.group(1) if m else "unknown"


@dataclass
class ResolvedDevice:
    device: Device
    device_hash: str
    ip_hash: str
    from_token: bool
    token_mismatch: bool
    is_new: bool
    device_token: str


def _fingerprint_hash(signals: DeviceSignals) -> str:
    normalized = signals.normalized()
    if normalized.strip("|") == "":
        # No usable signals: fall back to a coarse network+UA bucket so that the
        # request still gets *some* identity, but mark it weak.
        normalized = "weak:" + hashlib.sha256(
            f"{signals.ip}|{signals.ua_family()}".encode()
        ).hexdigest()[:24]
    return hash_device_signals(normalized)


def resolve_device(db: Session, signals: DeviceSignals) -> ResolvedDevice:
    """Find or create the device identity for this request."""
    fp_hash = _fingerprint_hash(signals)
    ip_hash = hash_ip(signals.ip)

    token_payload = verify_device_token(signals.device_token)
    device: Optional[Device] = None
    from_token = False
    token_mismatch = False

    if token_payload:
        device = db.execute(
            select(Device).where(Device.id == token_payload["did"])
        ).scalar_one_or_none()
        if device and device.token_version == int(token_payload.get("v", 1)):
            from_token = True
            token_mismatch = device.device_hash[:32] != token_payload.get("dh")
        else:
            device = None  # revoked/rotated token -> ignore

    if device is None:
        device = db.execute(
            select(Device).where(Device.device_hash == fp_hash)
        ).scalar_one_or_none()

    is_new = device is None
    if is_new:
        device = Device(
            device_hash=fp_hash,
            first_ip_hash=ip_hash,
            last_ip_hash=ip_hash,
            user_agent_family=signals.ua_family(),
        )
        db.add(device)
        try:
            db.flush()
        except IntegrityError:  # pragma: no cover - concurrent insert
            db.rollback()
            device = db.execute(
                select(Device).where(Device.device_hash == fp_hash)
            ).scalar_one()
            is_new = False
    else:
        device.last_ip_hash = ip_hash
        device.last_seen_at = utcnow()
        db.flush()

    return ResolvedDevice(
        device=device,
        device_hash=device.device_hash,
        ip_hash=ip_hash,
        from_token=from_token,
        token_mismatch=token_mismatch,
        is_new=is_new,
        device_token=issue_device_token(device.id, device.device_hash, device.token_version),
    )


def accounts_on_device(db: Session, device_id: str) -> List[str]:
    rows = db.execute(select(UserDevice.user_id).where(UserDevice.device_id == device_id)).all()
    return [r[0] for r in rows]


def devices_of_user(db: Session, user_id: str) -> List[str]:
    rows = db.execute(select(UserDevice.device_id).where(UserDevice.user_id == user_id)).all()
    return [r[0] for r in rows]


def link_user_device(db: Session, user_id: str, device: Device, ip_hash: str = "") -> None:
    exists = db.execute(
        select(UserDevice).where(UserDevice.user_id == user_id, UserDevice.device_id == device.id)
    ).scalar_one_or_none()
    if exists:
        return
    is_primary = device.account_count == 0
    db.add(UserDevice(user_id=user_id, device_id=device.id, is_primary=is_primary))
    device.account_count += 1
    device.last_seen_at = utcnow()
    db.flush()
    audit_service.log(
        db,
        AuditAction.DEVICE_REGISTERED,
        "device",
        device.id,
        actor_user_id=user_id,
        meta={"accountCount": device.account_count, "primary": is_primary},
        ip_hash=ip_hash,
    )


def rotate_device_token(db: Session, device: Device) -> str:
    """Rotation/revocation: bump the version and re-issue."""
    device.token_version += 1
    db.flush()
    return issue_device_token(device.id, device.device_hash, device.token_version)
