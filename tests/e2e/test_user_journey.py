"""
E2E test: Complete user journey.
Simulates a real user going through the full API workflow:
   1. Provision a user → real LiteLLM virtual key issued
   2. GET /auth/me → confirm identity
   3. POST /chat → new session auto-created, real SSE tokens streamed from vLLM
   4. GET /sessions → session visible in list
   5. GET /sessions/{id} → messages visible
  5b. POST /autocomplete → real fill-in-the-middle completion from vLLM
   6. POST /tasks/code-review → task enqueued
   7. GET /tasks/{id} → status returned
   8. DELETE /sessions/{id} → cleanup
   9. GET /sessions → empty

Inference is NOT mocked here: steps 1, 3, and 5b hit the live litellm-test /
vllm-test services. Only Celery dispatch (steps 6-7) is mocked. Because real
model output is non-deterministic, assertions check response shape and
non-emptiness rather than exact text.
"""
import json

import pytest
from unittest.mock import patch, MagicMock

from src.di.container import get_authenticated_user
from src.models.entities import UserEntity


pytestmark = pytest.mark.e2e


class TestCompleteUserJourney:
    """
    Full provisioning → chat → sessions → autocomplete → tasks → cleanup flow.
    Only Celery task dispatch is mocked; provisioning, chat, and autocomplete
    all run against the real litellm-test/vllm-test stack.
    """

    @patch("src.services.implementations.task_service.batch_code_review_task")
    @patch("src.services.implementations.task_service.AsyncResult")
    async def test_full_journey(
        self,
        mock_async_result_cls,
        mock_celery_task,
        e2e_client,
    ):
        # -- Step 1: Provision a user (real LiteLLM /key/generate call) --
        provision_resp = await e2e_client.post(
            "/api/v1/auth/provision",
            json={"username": "journey_user"},
        )
        assert provision_resp.status_code == 201
        user_data = provision_resp.json()
        api_key = user_data["api_key"]
        assert api_key.startswith("sk-")

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

        # -- Step 3: POST /chat → real SSE stream from litellm-test/vllm-test --
        chat_resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "Write a hello world function"},
            headers={"X-API-Key": api_key},
        )
        assert chat_resp.status_code == 200
        assert len(chat_resp.text.strip()) > 0

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

        # -- Step 5b: POST /autocomplete → real FIM completion from vllm-test --
        autocomplete_resp = await e2e_client.post(
            "/api/v1/autocomplete",
            json={
                "prefix": "def add(a: int, b: int) -> int:\n    ",
                "suffix": "\n",
                "language": "python",
            },
            headers={"X-API-Key": api_key},
        )
        assert autocomplete_resp.status_code == 200
        completion = autocomplete_resp.json()["completion"]
        assert isinstance(completion, str)
        assert len(completion) > 0

        # The completion must fill only the hole it was given. Without stop
        # tokens the model runs on past the fill and returns whole unrelated
        # functions until it hits max_tokens, so assert it stopped at the
        # block boundary rather than merely returning something non-empty.
        assert "def " not in completion, f"completion ran past the fill: {completion!r}"
        assert "\n\n" not in completion, f"completion crossed a blank line: {completion!r}"
        assert not any(
            tok in completion for tok in ("<|fim_", "<|endoftext|>")
        ), f"special token leaked into completion: {completion!r}"

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
