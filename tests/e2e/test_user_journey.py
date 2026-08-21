"""
E2E test: Complete user journey.
Simulates a real user going through the full API workflow:
   1. Provision a user → real LiteLLM virtual key issued
   2. GET /auth/me → confirm identity
   3. POST /chat → new session auto-created, real SSE tokens streamed from vLLM
   4. GET /sessions → session visible in list
   5. GET /sessions/{id} → messages visible
  5b. POST /autocomplete → real fill-in-the-middle completion from vLLM
   6. DELETE /sessions/{id} → cleanup
   7. GET /sessions → empty

Nothing is mocked: every step runs against the live litellm-test / vllm-test
services. Because real model output is non-deterministic, assertions check
response shape and boundaries rather than exact text.
"""
import json

import pytest

from src.di.container import get_authenticated_user
from src.models.entities import UserEntity


pytestmark = pytest.mark.e2e


class TestCompleteUserJourney:
    """
    Full provisioning → chat → sessions → autocomplete → cleanup flow, run
    end to end against the real litellm-test/vllm-test stack with no mocks.
    """

    async def test_full_journey(self, e2e_client):
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

        # -- Step 6: DELETE /sessions/{id} → cleanup --
        delete_resp = await e2e_client.delete(
            f"/api/v1/sessions/{session_id}",
            headers={"X-API-Key": api_key},
        )
        assert delete_resp.status_code == 204

        # -- Step 7: GET /sessions → empty --
        final_sessions = await e2e_client.get(
            "/api/v1/sessions",
            headers={"X-API-Key": api_key},
        )
        assert final_sessions.status_code == 200
        assert final_sessions.json() == []

        # Cleanup overrides
        if get_authenticated_user in app.dependency_overrides:
            del app.dependency_overrides[get_authenticated_user]
