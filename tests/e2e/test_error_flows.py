"""
E2E test: Error scenario flows.
Verifies that the API returns correct error responses for invalid/unauthorized requests.
"""
import uuid

import pytest

from src.di.container import get_authenticated_user
from src.models.entities import UserEntity
from tests.conftest import TEST_USER_ID, TEST_USERNAME, TEST_API_KEY, FIXED_NOW


pytestmark = pytest.mark.e2e


class TestUnauthenticatedAccess:
    """All protected endpoints should reject requests without valid API key."""

    async def test_sessions_list_unauthenticated(self, e2e_client):
        resp = await e2e_client.get("/api/v1/sessions")
        assert resp.status_code in (401, 403)

    async def test_session_detail_unauthenticated(self, e2e_client):
        resp = await e2e_client.get(f"/api/v1/sessions/{uuid.uuid4()}")
        assert resp.status_code in (401, 403)

    async def test_session_delete_unauthenticated(self, e2e_client):
        resp = await e2e_client.delete(f"/api/v1/sessions/{uuid.uuid4()}")
        assert resp.status_code in (401, 403)

    async def test_chat_unauthenticated(self, e2e_client):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code in (401, 403)



class TestNotFoundScenarios:
    """Authenticated requests for nonexistent resources should return 404."""

    @pytest.fixture(autouse=True)
    def _setup_auth(self, e2e_client):
        """Override auth for these tests so we get past authentication."""
        from src.main import app

        async def override_auth():
            user = UserEntity(
                id=TEST_USER_ID,
                username=TEST_USERNAME,
                api_key=TEST_API_KEY,
                created_at=FIXED_NOW,
            )
            user.sessions = []
            return user

        app.dependency_overrides[get_authenticated_user] = override_auth
        yield
        if get_authenticated_user in app.dependency_overrides:
            del app.dependency_overrides[get_authenticated_user]

    async def test_get_nonexistent_session(self, e2e_client):
        resp = await e2e_client.get(f"/api/v1/sessions/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_delete_nonexistent_session(self, e2e_client):
        resp = await e2e_client.delete(f"/api/v1/sessions/{uuid.uuid4()}")
        assert resp.status_code == 404
