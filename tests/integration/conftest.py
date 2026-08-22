"""
Integration test fixtures.
Provides a FastAPI client backed by an in-memory SQLite database.
External services (LiteLLM) are mocked at the boundary.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.models.entities import Base
from src.di.container import get_db_session


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


async def override_get_db_session():
    async with TestSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Async test client
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client():
    """App client backed by the in-memory database. There is no auth layer."""
    from src.main import app

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
