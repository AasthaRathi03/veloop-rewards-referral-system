"""Request level idempotency helpers."""
import json
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import IdempotencyRecord


def get_stored_response(db: Session, scope: str, user_id: str, key: Optional[str]) -> Optional[Dict[str, Any]]:
    if not key:
        return None
    row = db.execute(
        select(IdempotencyRecord).where(
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.key == key,
        )
    ).scalar_one_or_none()
    return json.loads(row.response_body) if row else None


def store_response(db: Session, scope: str, user_id: str, key: Optional[str], body: Dict[str, Any]) -> None:
    if not key:
        return
    db.add(
        IdempotencyRecord(
            scope=scope, user_id=user_id, key=key, response_body=json.dumps(body, default=str)
        )
    )
    try:
        db.flush()
    except IntegrityError:  # concurrent duplicate - the stored copy wins
        db.rollback()
