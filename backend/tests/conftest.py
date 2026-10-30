"""Pytest fixtures and configuration."""

import asyncio
import os
import uuid
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy import event, select

# Disable GeoAlchemy2 SpatiaLite triggers on in-memory SQLite for test runner
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
except Exception:
    pass

# Set test environment
os.environ["SENTINEL_ENVIRONMENT"] = "local"
os.environ["SENTINEL_DEMO_MODE"] = "true"
os.environ["SENTINEL_SECRET_KEY"] = "test-secret-key-at-least-32-chars-long"

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.tenant import Membership, MembershipRole, Tenant, User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        # Seed test tenants idempotently
        res = await session.execute(select(Tenant).where(Tenant.slug == "district_health_authority"))
        t1 = res.scalar_one_or_none()
        if not t1:
            t1 = Tenant(id=uuid.uuid4(), name="Tenant Alpha", slug="district_health_authority", is_active=True)
            t2 = Tenant(id=uuid.uuid4(), name="Tenant Beta", slug="greenfield_industries", is_active=True)
            session.add_all([t1, t2])
            await session.flush()

            u1 = User(id=uuid.uuid4(), email="analyst@demo.local", external_id="demo-sub-analyst", display_name="Test Analyst", is_active=True)
            u2 = User(id=uuid.uuid4(), email="safety@greenfield.local", external_id="demo-sub-safety", display_name="Safety Manager", is_active=True)
            session.add_all([u1, u2])
            await session.flush()

            m1 = Membership(user_id=u1.id, tenant_id=t1.id, role=MembershipRole.PUBLIC_HEALTH_ANALYST, is_active=True)
            m2 = Membership(user_id=u2.id, tenant_id=t2.id, role=MembershipRole.WORKPLACE_SAFETY_MANAGER, is_active=True)
            session.add_all([m1, m2])
            await session.commit()

        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict:
    return {"Authorization": "Bearer demo-token-analyst-public_health_analyst"}


@pytest.fixture
def auth_headers_tenant_a() -> dict:
    return {"Authorization": "Bearer demo-token-analyst-public_health_analyst"}


@pytest.fixture
def auth_headers_tenant_b() -> dict:
    return {"Authorization": "Bearer demo-token-safety-workplace_safety_manager"}

