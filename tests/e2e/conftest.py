"""
E2E test fixtures.
Reuses integration DB setup but focused on multi-step journey flows.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.models.entities import Base
from src.di.container import get_db_session


# ---------------------------------------------------------------------------
# In-memory SQLite (separate engine from integration to avoid conflicts)
# ---------------------------------------------------------------------------
E2E_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

e2e_engine = create_async_engine(E2E_DATABASE_URL, echo=False)

E2ESessionLocal = async_sessionmaker(
    bind=e2e_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@event.listens_for(e2e_engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_e2e_database():
    async with e2e_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with e2e_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db_session():
    async with E2ESessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def e2e_client():
    """Full app client with real auth flow (no auth bypass)."""
    from src.main import app

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
