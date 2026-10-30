"""Declarative base with UUID primary-key and timestamp mixins."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# SQLite compatibility for GeoAlchemy2 when running without SpatiaLite
try:
    from sqlalchemy.ext.compiler import compiles
    from geoalchemy2.types import Geometry
    from geoalchemy2.admin.dialects import sqlite
    sqlite.before_create = lambda *args, **kwargs: None
    sqlite.after_create = lambda *args, **kwargs: None
    sqlite.before_drop = lambda *args, **kwargs: None
    sqlite.after_drop = lambda *args, **kwargs: None
    sqlite.setup_create_drop = lambda *args, **kwargs: None

    @compiles(Geometry, "sqlite")
    def compile_geometry_sqlite(element, compiler, **kw):
        return "BLOB"

    # Disable AsEWKB wrapper and GeomFromEWKT on column select/insert for SQLite compatibility
    _orig_col_expr = Geometry.column_expression
    def _column_expression_sqlite_safe(self, col):
        return col
    Geometry.column_expression = _column_expression_sqlite_safe

    _orig_bind_expr = Geometry.bind_expression
    def _bind_expression_sqlite_safe(self, bindvalue):
        return bindvalue
    Geometry.bind_expression = _bind_expression_sqlite_safe
except Exception:
    pass


class UUIDMixin:
    """Provides a UUID primary key column."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )


class TimestampMixin:
    """Provides created_at and updated_at columns in UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Base(DeclarativeBase):
    """Application-wide declarative base."""

    pass
