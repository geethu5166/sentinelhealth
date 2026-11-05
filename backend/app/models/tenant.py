"""Tenant, User, Membership, and RoleScope models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

__all__ = [
    "MembershipRole",
    "Tenant",
    "User",
    "Membership",
    "RoleScope",
]


class MembershipRole(str, enum.Enum):
    PUBLIC_HEALTH_ANALYST = "public_health_analyst"
    OCCUPATIONAL_HEALTH_ANALYST = "occupational_health_analyst"
    WORKPLACE_SAFETY_MANAGER = "workplace_safety_manager"
    DATA_STEWARD = "data_steward"
    PRIVACY_OFFICER = "privacy_officer"
    PLATFORM_ADMIN = "platform_admin"
    REGULATOR = "regulator"


class Tenant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    memberships: Mapped[list[Membership]] = relationship("Membership", back_populates="tenant", lazy="selectin")


class User(Base, UUIDMixin):
    __tablename__ = "users"

    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    memberships: Mapped[list[Membership]] = relationship(
        "Membership",
        back_populates="user",
        lazy="selectin",
        foreign_keys="Membership.user_id",
    )


class Membership(Base, UUIDMixin):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", "role", name="uq_membership_user_tenant_role"),
        Index("ix_membership_tenant_user", "tenant_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, name="membership_role", values_callable=lambda x: [e.value for e in x], create_constraint=True),
        nullable=False,
    )
    scopes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="memberships", foreign_keys=[user_id])
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="memberships")
    role_scopes: Mapped[list[RoleScope]] = relationship("RoleScope", back_populates="membership", lazy="selectin")


class RoleScope(Base, UUIDMixin):
    __tablename__ = "role_scopes"

    membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)  # geography, source, purpose
    scope_value: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    membership: Mapped[Membership] = relationship("Membership", back_populates="role_scopes")
