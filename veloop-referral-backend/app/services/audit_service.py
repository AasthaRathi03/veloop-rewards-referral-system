"""Append-only audit logging."""
import json
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import AuditLog


def log(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    ip_hash: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        meta=json.dumps(meta, default=str) if meta else None,
        ip_hash=ip_hash,
    )
    db.add(entry)
    db.flush()
    return entry
