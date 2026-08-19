"""
Integration tests for the chat route.
LiteLLM is mocked at the httpx boundary; everything inside — the route, the real
ChatService, and the real PostgresSessionRepository against in-memory SQLite —
runs for real, so session creation and message persistence are exercised end to end.
"""
import json
from contextlib import asynccontextmanager

import pytest
from unittest.mock import patch

from sqlalchemy.future import select

from src.models.entities import SessionEntity, MessageEntity
from tests.conftest import TEST_USER_ID
from tests.integration.conftest import TestSessionLocal


pytestmark = pytest.mark.integration


class _FakeStreamResponse:
    def __init__(self, lines):
        self._lines = lines
        self.status_code = 200

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeChatClient:
    def __init__(self, lines):
        self._lines = lines

    @asynccontextmanager
    async def stream(self, *args, **kwargs):
        yield _FakeStreamResponse(self._lines)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


_SSE_LINES = [
    'data: {"choices":[{"delta":{"content":"Hello "}}]}',
    'data: {"choices":[{"delta":{"content":"World"}}]}',
    "data: [DONE]",
]


class TestChatStream:
    @patch("src.services.implementations.chat_service.httpx.AsyncClient")
    async def test_streams_and_persists_session_and_messages(
        self, mock_client_cls, authenticated_client, seeded_user
    ):
        """POST /api/v1/chat auto-creates a session and persists both turns."""
        mock_client_cls.return_value = _FakeChatClient(_SSE_LINES)

        resp = await authenticated_client.post(
            "/api/v1/chat",
            json={"message": "Write a hello world function"},
        )

        assert resp.status_code == 200

        payloads = [
            json.loads(block[6:])
            for block in resp.text.strip().split("\n\n")
            if block.startswith("data: ")
        ]
        assert [p["content"] for p in payloads if not p["is_done"]] == ["Hello ", "World"]
        assert payloads[-1]["is_done"] is True

        session_id = payloads[0]["session_id"]

        # The real repository wrote a session and both messages.
        async with TestSessionLocal() as session:
            row = (await session.execute(
                select(SessionEntity).where(SessionEntity.user_id == TEST_USER_ID)
            )).scalar_one()
            assert str(row.id) == session_id
            assert row.title == "Write a hello world function"

            messages = (await session.execute(
                select(MessageEntity).where(MessageEntity.session_id == row.id)
            )).scalars().all()
            assert [(m.role, m.content) for m in messages] == [
                ("user", "Write a hello world function"),
                ("assistant", "Hello World"),
            ]

    @patch("src.services.implementations.chat_service.httpx.AsyncClient")
    async def test_unknown_session_id_auto_heals(
        self, mock_client_cls, authenticated_client, seeded_user
    ):
        """A session_id that doesn't exist creates a fresh session rather than 404ing."""
        mock_client_cls.return_value = _FakeChatClient(_SSE_LINES)
        missing_id = "11111111-1111-1111-1111-111111111111"

        resp = await authenticated_client.post(
            "/api/v1/chat",
            json={"message": "Recover please", "session_id": missing_id},
        )

        assert resp.status_code == 200
        first = json.loads(resp.text.strip().split("\n\n")[0][6:])
        assert first["session_id"] != missing_id

    async def test_unauthenticated_rejected(self, client):
        resp = await client.post("/api/v1/chat", json={"message": "hi"})

        assert resp.status_code in (401, 403)
