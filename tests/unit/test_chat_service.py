"""
Unit tests for ChatService.
SessionRepository and httpx (LiteLLM) calls are mocked.
"""
import json
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.implementations.chat_service import ChatService
from src.schemas.chat import ChatRequest
from tests.conftest import TEST_USER_ID, TEST_SESSION_ID, FIXED_NOW


pytestmark = pytest.mark.unit


def _build_service(session_repo=None, settings=None):
    if session_repo is None:
        session_repo = AsyncMock()
    if settings is None:
        settings = MagicMock()
        settings.LITELLM_URL = "http://litellm:4000"
        settings.DEFAULT_CODE_MODEL = "qwen-coder"
        settings.SYSTEM_PROMPT = "You are an expert AI coding assistant."
    return ChatService(session_repo, settings)


def _make_session_entity(session_id=TEST_SESSION_ID, user_id=TEST_USER_ID):
    from src.models.entities import SessionEntity
    s = SessionEntity(
        id=session_id,
        user_id=user_id,
        title="Test",
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
    )
    s.messages = []
    return s


def _make_message_entity(role="user", content="Hello"):
    from src.models.entities import MessageEntity
    m = MessageEntity(
        id=uuid.uuid4(),
        session_id=TEST_SESSION_ID,
        role=role,
        content=content,
        created_at=FIXED_NOW,
    )
    return m


from contextlib import asynccontextmanager


class _FakeStreamResponse:
    """Simulates httpx streaming response with SSE lines."""
    def __init__(self, lines):
        self._lines = lines
        self.status_code = 200

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeClient:
    def __init__(self, stream_response):
        self._stream_response = stream_response

    @asynccontextmanager
    async def stream(self, *args, **kwargs):
        yield self._stream_response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Session resolution
# ---------------------------------------------------------------------------
class TestSessionResolution:
    @patch("src.services.implementations.chat_service.httpx.AsyncClient")
    async def test_creates_new_session_when_no_id(self, mock_client_cls, mock_user_entity):
        new_session = _make_session_entity()
        repo = AsyncMock()
        repo.create.return_value = new_session
        repo.get_messages.return_value = [_make_message_entity()]

        # Minimal SSE stream
        sse_lines = [
            'data: {"choices":[{"delta":{"content":"Hi"}}]}',
            "data: [DONE]",
        ]
        fake_stream = _FakeStreamResponse(sse_lines)
        fake_client = _FakeClient(fake_stream)
        mock_client_cls.return_value = fake_client

        service = _build_service(session_repo=repo)
        request = ChatRequest(message="Hello AI")

        chunks = []
        async for chunk in service.stream_chat_response(request, mock_user_entity):
            chunks.append(chunk)

        repo.create.assert_awaited_once()
        call_args = repo.create.call_args
        assert (call_args.kwargs.get("title") == "Hello AI") or (len(call_args.args) > 1 and call_args.args[1] == "Hello AI")

    @patch("src.services.implementations.chat_service.httpx.AsyncClient")
    async def test_uses_existing_session(self, mock_client_cls, mock_user_entity):
        existing = _make_session_entity()
        repo = AsyncMock()
        repo.get_by_id.return_value = existing
        repo.get_messages.return_value = []

        sse_lines = ["data: [DONE]"]
        fake_stream = _FakeStreamResponse(sse_lines)
        fake_client = _FakeClient(fake_stream)
        mock_client_cls.return_value = fake_client

        service = _build_service(session_repo=repo)
        request = ChatRequest(message="Hi", session_id=TEST_SESSION_ID)

        async for _ in service.stream_chat_response(request, mock_user_entity):
            pass

        repo.get_by_id.assert_awaited_once_with(TEST_SESSION_ID, mock_user_entity.id)
        repo.create.assert_not_awaited()

    @patch("src.services.implementations.chat_service.httpx.AsyncClient")
    async def test_auto_heals_missing_session(self, mock_client_cls, mock_user_entity):
        repo = AsyncMock()
        repo.get_by_id.return_value = None  # session not found
        new_session = _make_session_entity()
        repo.create.return_value = new_session
        repo.get_messages.return_value = []

        sse_lines = ["data: [DONE]"]
        fake_stream = _FakeStreamResponse(sse_lines)
        fake_client = _FakeClient(fake_stream)
        mock_client_cls.return_value = fake_client

        service = _build_service(session_repo=repo)
        request = ChatRequest(message="Hi", session_id=TEST_SESSION_ID)

        async for _ in service.stream_chat_response(request, mock_user_entity):
            pass

        # Should create new session since the provided ID wasn't found
        repo.create.assert_awaited_once()


# ---------------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------------
class TestMessageHandling:
    @patch("src.services.implementations.chat_service.httpx.AsyncClient")
    async def test_appends_user_message(self, mock_client_cls, mock_user_entity):
        repo = AsyncMock()
        repo.create.return_value = _make_session_entity()
        repo.get_messages.return_value = [_make_message_entity()]

        sse_lines = ["data: [DONE]"]
        fake_stream = _FakeStreamResponse(sse_lines)
        fake_client = _FakeClient(fake_stream)
        mock_client_cls.return_value = fake_client

        service = _build_service(session_repo=repo)
        request = ChatRequest(message="Write a function")

        async for _ in service.stream_chat_response(request, mock_user_entity):
            pass

        # First call to append_message should be the user message
        repo.append_message.assert_any_await(TEST_SESSION_ID, "user", "Write a function")

    @patch("src.services.implementations.chat_service.httpx.AsyncClient")
    async def test_persists_assistant_response(self, mock_client_cls, mock_user_entity):
        repo = AsyncMock()
        repo.create.return_value = _make_session_entity()
        repo.get_messages.return_value = [_make_message_entity()]

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"def "}}]}',
            'data: {"choices":[{"delta":{"content":"hello():"}}]}',
            "data: [DONE]",
        ]
        fake_stream = _FakeStreamResponse(sse_lines)
        fake_client = _FakeClient(fake_stream)
        mock_client_cls.return_value = fake_client

        service = _build_service(session_repo=repo)
        request = ChatRequest(message="Write a function")

        async for _ in service.stream_chat_response(request, mock_user_entity):
            pass

        # Should persist the accumulated assistant response
        repo.append_message.assert_any_await(TEST_SESSION_ID, "assistant", "def hello():")


# ---------------------------------------------------------------------------
# SSE output
# ---------------------------------------------------------------------------
class TestSSEOutput:
    @patch("src.services.implementations.chat_service.httpx.AsyncClient")
    async def test_yields_sse_chunks(self, mock_client_cls, mock_user_entity):
        repo = AsyncMock()
        repo.create.return_value = _make_session_entity()
        repo.get_messages.return_value = []

        sse_lines = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            "data: [DONE]",
        ]
        fake_stream = _FakeStreamResponse(sse_lines)
        fake_client = _FakeClient(fake_stream)
        mock_client_cls.return_value = fake_client

        service = _build_service(session_repo=repo)
        request = ChatRequest(message="Hi")

        chunks = []
        async for chunk in service.stream_chat_response(request, mock_user_entity):
            chunks.append(chunk)

        # Should have at least the content chunk + final done chunk
        assert len(chunks) >= 2

        # First chunk should contain "Hello" content
        parsed_first = json.loads(chunks[0].split("data: ")[1].strip())
        assert parsed_first["content"] == "Hello"
        assert parsed_first["is_done"] is False

        # Last chunk should be the done signal
        parsed_last = json.loads(chunks[-1].split("data: ")[1].strip())
        assert parsed_last["is_done"] is True
