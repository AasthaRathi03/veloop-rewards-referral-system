from typing import Optional

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class AuditLog(UUIDMixin, TimestampMixin, Base):
    """Append-only audit trail for referral/reward/fraud events."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_action_created", "action", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    meta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
