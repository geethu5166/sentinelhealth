"""Geography, Workplace, and related models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

__all__ = [
    "GeographyLevel",
    "Geography",
    "GeographyVersion",
    "Workplace",
    "WorkplaceGeographyLink",
]


class GeographyLevel(str, enum.Enum):
    DISTRICT = "district"
    SUB_DISTRICT = "sub_district"
    WARD = "ward"
    SITE = "site"


class Geography(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "geographies"
    __table_args__ = (
        Index("ix_geography_tenant_code", "tenant_id", "code"),
        Index("ix_geography_tenant_level", "tenant_id", "level"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[GeographyLevel] = mapped_column(
        Enum(GeographyLevel, name="geography_level", values_callable=lambda x: [e.value for e in x], create_constraint=True),
        nullable=False,
    )
    geometry: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographies.id"), nullable=True
    )
    population_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    population_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    properties: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    parent: Mapped[Geography | None] = relationship("Geography", remote_side="Geography.id", lazy="selectin")
    versions: Mapped[list[GeographyVersion]] = relationship("GeographyVersion", back_populates="geography")
    workplaces: Mapped[list[Workplace]] = relationship("Workplace", back_populates="geography")


class GeographyVersion(Base, UUIDMixin):
    __tablename__ = "geography_versions"

    geography_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographies.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    geometry: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True
    )
    properties: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    geography: Mapped[Geography] = relationship("Geography", back_populates="versions")


class Workplace(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workplaces"
    __table_args__ = (
        Index("ix_workplace_tenant_code", "tenant_id", "code"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    site_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )
    address_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    geography_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographies.id"), nullable=True
    )
    worker_count_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    worker_count_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    properties: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    geography: Mapped[Geography | None] = relationship("Geography", back_populates="workplaces")
    geography_links: Mapped[list[WorkplaceGeographyLink]] = relationship(
        "WorkplaceGeographyLink", back_populates="workplace"
    )


class WorkplaceGeographyLink(Base, UUIDMixin):
    __tablename__ = "workplace_geography_links"

    workplace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workplaces.id", ondelete="CASCADE"), nullable=False
    )
    geography_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geographies.id", ondelete="CASCADE"), nullable=False
    )
    link_type: Mapped[str] = mapped_column(String(50), nullable=False)  # administrative, catchment, environmental_grid
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    mapping_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workplace: Mapped[Workplace] = relationship("Workplace", back_populates="geography_links")
    geography: Mapped[Geography] = relationship("Geography")
