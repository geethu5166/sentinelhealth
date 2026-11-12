"""Notification outbox and delivery models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin, pg_enum

__all__ = [
    "NotificationType",
    "NotificationChannel",
    "NotificationStatus",
    "NotificationOutbox",
    "NotificationDelivery",
]


class NotificationType(str, enum.Enum):
    ALERT_NEW = "alert_new"
    ALERT_ESCALATION = "alert_escalation"
    TASK_ASSIGNED = "task_assigned"
    TASK_OVERDUE = "task_overdue"
    TASK_REMINDER = "task_reminder"
    SYSTEM = "system"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    EXPIRED = "expired"


class NotificationOutbox(Base, UUIDMixin):
    """Reliable outbox queue for notifications."""

    __tablename__ = "notification_outbox"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("preventive_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        pg_enum(NotificationType, "notification_type_enum"),
        nullable=False,
    )
    recipient_role: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        pg_enum(NotificationChannel, "notification_channel_enum"),
        default=NotificationChannel.IN_APP,
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_template: Mapped[str] = mapped_column(String(100), nullable=False)
    body_params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        pg_enum(NotificationStatus, "notification_status_enum"),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        "NotificationDelivery",
        back_populates="outbox_item",
        cascade="all, delete-orphan",
    )


class NotificationDelivery(Base, UUIDMixin):
    """Delivery attempt log for an outbox notification."""

    __tablename__ = "notification_deliveries"

    outbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_outbox.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        pg_enum(NotificationChannel, "notification_channel_enum"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    outbox_item: Mapped[NotificationOutbox] = relationship(
        "NotificationOutbox",
        back_populates="deliveries",
    )

