"""
Integration test fixtures.
Provides a FastAPI TestClient backed by an in-memory SQLite database.
External services (LiteLLM, Celery) are mocked at the boundary.
"""
import uuid
from datetime import datetime, UTC

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.models.entities import Base, UserEntity
from src.di.container import get_db_session, get_authenticated_user
from src.config.settings import get_settings

from tests.conftest import TEST_USER_ID, TEST_USERNAME, TEST_API_KEY, FIXED_NOW


# ---------------------------------------------------------------------------
# In-memory SQLite async engine
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Enable foreign keys for SQLite (disabled by default)
# ---------------------------------------------------------------------------
@event.listens_for(test_engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ---------------------------------------------------------------------------
# DB lifecycle: create tables before each test, drop after
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Override get_db_session dependency
# ---------------------------------------------------------------------------
async def override_get_db_session():
    async with TestSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Seed a test user directly in the DB
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def seeded_user() -> UserEntity:
    async with TestSessionLocal() as session:
        user = UserEntity(
            id=TEST_USER_ID,
            username=TEST_USERNAME,
            api_key=TEST_API_KEY,
            created_at=FIXED_NOW,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# ---------------------------------------------------------------------------
# Mock authenticated user dependency
# ---------------------------------------------------------------------------
def _make_mock_user():
    user = UserEntity(
        id=TEST_USER_ID,
        username=TEST_USERNAME,
        api_key=TEST_API_KEY,
        created_at=FIXED_NOW,
    )
    user.sessions = []
    user.tasks = []
    return user


async def override_get_authenticated_user():
    return _make_mock_user()


# ---------------------------------------------------------------------------
# Async test client with dependency overrides
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client():
    """Unauthenticated client — no auth override."""
    from src.main import app

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_client():
    """Client with authentication bypassed — all routes see seeded user."""
    from src.main import app

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_authenticated_user] = override_get_authenticated_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
