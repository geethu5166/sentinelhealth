"""Async SQLAlchemy engine, session factory, and tenant context helper."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Set the PostgreSQL session variable used by row-level security policies.

    Uses set_config(..., is_local=true) so the value can be bound as a parameter.
    Plain ``SET LOCAL ... = :tid`` is rejected by PostgreSQL/asyncpg and, if the
    error is swallowed, leaves the open transaction aborted.
    """
    bind = session.bind
    if bind is not None and getattr(bind.dialect, "name", None) == "sqlite":
        return
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )


async def reset_tenant_context(session: AsyncSession) -> None:
    """Explicitly reset the PostgreSQL tenant session variable to prevent pooled connection leakage."""
    bind = session.bind
    if bind is not None and getattr(bind.dialect, "name", None) == "sqlite":
        return
    try:
        await session.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))
    except Exception:
        pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session and ensures cleanup."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await reset_tenant_context(session)
            await session.close()
