"""
E2E test: Complete user journey.
Simulates a real user going through the full API workflow:
  1. Provision a user → get API key
  2. GET /auth/me → confirm identity
  3. POST /chat → new session auto-created, SSE streamed
  4. GET /sessions → session visible in list
  5. GET /sessions/{id} → messages visible
  6. POST /tasks/code-review → task enqueued
  7. GET /tasks/{id} → status returned
  8. DELETE /sessions/{id} → cleanup
  9. GET /sessions → empty
"""
import json

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.di.container import get_authenticated_user
from src.models.entities import UserEntity


pytestmark = pytest.mark.e2e


class TestCompleteUserJourney:
    """
    Full provisioning → chat → sessions → tasks → cleanup flow.
    LiteLLM and Celery are mocked but everything else runs through the real stack.
    """

    @patch("src.services.implementations.task_service.batch_code_review_task")
    @patch("src.services.implementations.task_service.AsyncResult")
    async def test_full_journey(
        self,
        mock_async_result_cls,
        mock_celery_task,
        e2e_client,
    ):
        # -- Step 1: Provision a user --
        mock_auth_response = MagicMock()
        mock_auth_response.status_code = 200
        mock_auth_response.json.return_value = {"key": "sk-journey-key"}

        mock_auth_instance = AsyncMock()
        mock_auth_instance.post.return_value = mock_auth_response
        mock_auth_instance.__aenter__ = AsyncMock(return_value=mock_auth_instance)
        mock_auth_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.implementations.auth_service.httpx.AsyncClient", return_value=mock_auth_instance):
            provision_resp = await e2e_client.post(
                "/api/v1/auth/provision",
                json={"username": "journey_user"},
            )
            assert provision_resp.status_code == 201
            user_data = provision_resp.json()
            api_key = user_data["api_key"]
            assert api_key == "sk-journey-key"

        # -- Step 2: GET /auth/me --
        from src.main import app
        import uuid

        async def override_auth():
            user = UserEntity(
                id=uuid.UUID(user_data["id"]) if isinstance(user_data["id"], str) else user_data["id"],
                username="journey_user",
                api_key=api_key,
            )
            user.sessions = []
            user.tasks = []
            return user

        app.dependency_overrides[get_authenticated_user] = override_auth

        me_resp = await e2e_client.get(
            "/api/v1/auth/me",
            headers={"X-API-Key": api_key},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "journey_user"

        # -- Step 3: POST /chat → SSE streaming --
        from contextlib import asynccontextmanager

        class _FakeStreamResponse:
            def __init__(self):
                self.status_code = 200

            async def aiter_lines(self):
                yield 'data: {"choices":[{"delta":{"content":"Hello "}}]}'
                yield 'data: {"choices":[{"delta":{"content":"World"}}]}'
                yield "data: [DONE]"

        class _FakeChatClient:
            @asynccontextmanager
            async def stream(self, *args, **kwargs):
                yield _FakeStreamResponse()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        with patch("src.services.implementations.chat_service.httpx.AsyncClient", return_value=_FakeChatClient()):
            chat_resp = await e2e_client.post(
                "/api/v1/chat",
                json={"message": "Write a hello world function"},
                headers={"X-API-Key": api_key},
            )
            assert chat_resp.status_code == 200

        # Parse SSE response to extract session_id
        sse_lines = chat_resp.text.strip().split("\n\n")
        session_id = None
        for line in sse_lines:
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if "session_id" in payload:
                    session_id = payload["session_id"]
                    break
        assert session_id is not None

        # -- Step 4: GET /sessions → session visible --
        sessions_resp = await e2e_client.get(
            "/api/v1/sessions",
            headers={"X-API-Key": api_key},
        )
        assert sessions_resp.status_code == 200
        sessions = sessions_resp.json()
        assert len(sessions) >= 1
        session_titles = [s["title"] for s in sessions]
        # Title should be truncated from the chat message
        assert any("Write a hello world" in t for t in session_titles)

        # -- Step 5: GET /sessions/{id} → messages visible --
        detail_resp = await e2e_client.get(
            f"/api/v1/sessions/{session_id}",
            headers={"X-API-Key": api_key},
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail["messages"]) >= 1
        roles = [m["role"] for m in detail["messages"]]
        assert "user" in roles

        # -- Step 6: POST /tasks/code-review → task enqueued --
        mock_job = MagicMock()
        mock_job.id = "journey-task-001"
        mock_celery_task.delay.return_value = mock_job

        task_resp = await e2e_client.post(
            "/api/v1/tasks/code-review",
            json={"files": [{"filename": "app.py", "code": "def main(): pass"}]},
            headers={"X-API-Key": api_key},
        )
        assert task_resp.status_code == 200
        task_data = task_resp.json()
        assert task_data["task_id"] == "journey-task-001"
        assert task_data["status"] == "QUEUED"

        # -- Step 7: GET /tasks/{id} → status returned --
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_result.ready.return_value = False
        mock_result.info = None
        mock_async_result_cls.return_value = mock_result

        status_resp = await e2e_client.get(
            "/api/v1/tasks/journey-task-001",
            headers={"X-API-Key": api_key},
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "PENDING"

        # -- Step 8: DELETE /sessions/{id} → cleanup --
        delete_resp = await e2e_client.delete(
            f"/api/v1/sessions/{session_id}",
            headers={"X-API-Key": api_key},
        )
        assert delete_resp.status_code == 204

        # -- Step 9: GET /sessions → empty --
        final_sessions = await e2e_client.get(
            "/api/v1/sessions",
            headers={"X-API-Key": api_key},
        )
        assert final_sessions.status_code == 200
        assert final_sessions.json() == []

        # Cleanup overrides
        if get_authenticated_user in app.dependency_overrides:
            del app.dependency_overrides[get_authenticated_user]
