"""
E2E test: complete session journey.

Simulates real use of the single-user platform:
  1. POST /chat            → a session is auto-created, real SSE tokens stream
  2. GET  /sessions        → the session appears in the list
  3. GET  /sessions/{id}   → both turns are persisted
  4. POST /chat again      → continuing the same session appends to it
  5. DELETE /sessions/{id} → cleanup
  6. GET  /sessions        → empty

Nothing is mocked: every step runs against the live litellm/vllm stack. Because
real model output is non-deterministic, assertions check response shape and
persistence rather than exact text.
"""
import json

import pytest


pytestmark = pytest.mark.e2e


def _parse_sse(text):
    """Return the decoded SSE payloads from a chat response body."""
    return [
        json.loads(block[6:])
        for block in text.strip().split("\n\n")
        if block.startswith("data: ")
    ]


class TestCompleteSessionJourney:
    async def test_full_journey(self, e2e_client):
        # -- Step 1: chat with no session_id auto-creates one --
        chat_resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "Write a hello world function"},
        )
        assert chat_resp.status_code == 200
        assert len(chat_resp.text.strip()) > 0

        payloads = _parse_sse(chat_resp.text)
        assert payloads, "no SSE payloads returned"
        session_id = payloads[0]["session_id"]
        assert payloads[-1]["is_done"] is True

        streamed = "".join(p["content"] for p in payloads if not p["is_done"])
        assert len(streamed) > 0, "model streamed no content"

        # -- Step 2: the session is listed --
        sessions_resp = await e2e_client.get("/api/v1/sessions")
        assert sessions_resp.status_code == 200
        sessions = sessions_resp.json()
        assert len(sessions) == 1
        assert sessions[0]["id"] == session_id
        assert "Write a hello world" in sessions[0]["title"]

        # -- Step 3: both turns were persisted --
        detail_resp = await e2e_client.get(f"/api/v1/sessions/{session_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        roles = [m["role"] for m in detail["messages"]]
        assert roles == ["user", "assistant"]
        assert detail["messages"][0]["content"] == "Write a hello world function"
        assert len(detail["messages"][1]["content"]) > 0

        # -- Step 4: continuing the same session appends rather than branching --
        follow_up = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "Now make it take a name argument", "session_id": session_id},
        )
        assert follow_up.status_code == 200
        assert _parse_sse(follow_up.text)[0]["session_id"] == session_id

        assert len((await e2e_client.get("/api/v1/sessions")).json()) == 1

        detail = (await e2e_client.get(f"/api/v1/sessions/{session_id}")).json()
        assert [m["role"] for m in detail["messages"]] == [
            "user", "assistant", "user", "assistant",
        ]

        # -- Step 5: delete --
        delete_resp = await e2e_client.delete(f"/api/v1/sessions/{session_id}")
        assert delete_resp.status_code == 204

        # -- Step 6: empty again --
        final = await e2e_client.get("/api/v1/sessions")
        assert final.status_code == 200
        assert final.json() == []
