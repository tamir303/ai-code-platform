"""
Integration tests for session routes.
Tests GET/DELETE /sessions through the full FastAPI stack with in-memory DB.
"""
import uuid

import pytest

from src.models.entities import SessionEntity, MessageEntity
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


async def _seed_messages(session_id=TEST_SESSION_ID, count=5):
    """Insert multiple messages into a session."""
    async with TestSessionLocal() as session:
        for i in range(count):
            msg = MessageEntity(
                id=uuid.uuid4(),
                session_id=session_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i + 1}",
                created_at=FIXED_NOW,
            )
            session.add(msg)
        await session.commit()


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

    async def test_pagination_params(self, authenticated_client, seeded_user):
        """GET /api/v1/sessions with limit and offset query parameters."""
        await _seed_session(title="Session 1")

        resp = await authenticated_client.get("/api/v1/sessions?limit=10&offset=0")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp_offset = await authenticated_client.get("/api/v1/sessions?limit=10&offset=1")
        assert resp_offset.status_code == 200
        assert resp_offset.json() == []

    async def test_invalid_pagination_limit(self, authenticated_client, seeded_user):
        """GET /api/v1/sessions with invalid limit (> 100 or < 1) returns 422."""
        resp_too_high = await authenticated_client.get("/api/v1/sessions?limit=101")
        assert resp_too_high.status_code == 422

        resp_too_low = await authenticated_client.get("/api/v1/sessions?limit=0")
        assert resp_too_low.status_code == 422


class TestGetSessionDetail:
    async def test_found(self, authenticated_client, seeded_user):
        """GET /api/v1/sessions/{id} returns session with messages and pagination metadata."""
        await _seed_session()
        await _seed_messages(count=3)

        resp = await authenticated_client.get(f"/api/v1/sessions/{TEST_SESSION_ID}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(TEST_SESSION_ID)
        assert data["title"] == "Seeded Session"
        assert len(data["messages"]) == 3
        assert data["total_messages"] == 3
        assert data["limit"] == 50
        assert data["offset"] == 0

    async def test_messages_pagination(self, authenticated_client, seeded_user):
        """GET /api/v1/sessions/{id}?limit=2&offset=1 returns a paginated slice."""
        await _seed_session()
        await _seed_messages(count=5)

        resp = await authenticated_client.get(f"/api/v1/sessions/{TEST_SESSION_ID}?limit=2&offset=1")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["content"] == "Message 2"
        assert data["messages"][1]["content"] == "Message 3"
        assert data["total_messages"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 1

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
