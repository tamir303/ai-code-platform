"""
Integration tests for session routes.
Tests GET/DELETE /sessions through the full FastAPI stack with in-memory DB.
"""
import uuid

import pytest

from src.models.entities import SessionEntity
from tests.conftest import TEST_USER_ID, TEST_SESSION_ID, FIXED_NOW
from tests.integration.conftest import TestSessionLocal


pytestmark = pytest.mark.integration


async def _seed_session(user_id=TEST_USER_ID, title="Seeded Session"):
    """Insert a session directly into the test DB."""
    async with TestSessionLocal() as session:
        entity = SessionEntity(
            id=TEST_SESSION_ID,
            user_id=user_id,
            title=title,
            created_at=FIXED_NOW,
            updated_at=FIXED_NOW,
        )
        session.add(entity)
        await session.commit()
        return entity


class TestListSessions:
    async def test_empty(self, authenticated_client, seeded_user):
        """GET /api/v1/sessions returns empty list when no sessions exist."""
        resp = await authenticated_client.get("/api/v1/sessions")

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_with_data(self, authenticated_client, seeded_user):
        """GET /api/v1/sessions returns sessions after seeding."""
        await _seed_session()

        resp = await authenticated_client.get("/api/v1/sessions")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Seeded Session"


class TestGetSessionDetail:
    async def test_found(self, authenticated_client, seeded_user):
        """GET /api/v1/sessions/{id} returns session with messages."""
        await _seed_session()

        resp = await authenticated_client.get(f"/api/v1/sessions/{TEST_SESSION_ID}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(TEST_SESSION_ID)
        assert data["title"] == "Seeded Session"
        assert data["messages"] == []

    async def test_not_found(self, authenticated_client, seeded_user):
        """GET /api/v1/sessions/{id} with nonexistent ID returns 404."""
        fake_id = uuid.uuid4()

        resp = await authenticated_client.get(f"/api/v1/sessions/{fake_id}")

        assert resp.status_code == 404


class TestDeleteSession:
    async def test_success(self, authenticated_client, seeded_user):
        """DELETE /api/v1/sessions/{id} returns 204."""
        await _seed_session()

        resp = await authenticated_client.delete(f"/api/v1/sessions/{TEST_SESSION_ID}")

        assert resp.status_code == 204

        # Verify it's gone
        resp2 = await authenticated_client.get(f"/api/v1/sessions/{TEST_SESSION_ID}")
        assert resp2.status_code == 404

    async def test_not_found(self, authenticated_client, seeded_user):
        """DELETE /api/v1/sessions/{id} with nonexistent ID returns 404."""
        fake_id = uuid.uuid4()

        resp = await authenticated_client.delete(f"/api/v1/sessions/{fake_id}")

        assert resp.status_code == 404
