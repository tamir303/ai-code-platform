"""
E2E error matrices: how the API behaves for missing resources and bad input.

There is no authentication layer — this is a single-user local platform — so
these cover the 404 and 422 paths rather than 401/403.
"""
import uuid

import pytest


pytestmark = pytest.mark.e2e


class TestNotFoundScenarios:
    async def test_get_nonexistent_session(self, e2e_client):
        resp = await e2e_client.get(f"/api/v1/sessions/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_delete_nonexistent_session(self, e2e_client):
        resp = await e2e_client.delete(f"/api/v1/sessions/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestValidationScenarios:
    async def test_malformed_session_id_rejected(self, e2e_client):
        resp = await e2e_client.get("/api/v1/sessions/not-a-uuid")
        assert resp.status_code == 422

    async def test_chat_requires_message(self, e2e_client):
        resp = await e2e_client.post("/api/v1/chat", json={})
        assert resp.status_code == 422

    async def test_session_list_rejects_bad_pagination(self, e2e_client):
        resp = await e2e_client.get("/api/v1/sessions?limit=0")
        assert resp.status_code == 422
