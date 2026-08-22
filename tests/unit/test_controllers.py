"""
Unit tests for all controllers.
Controllers are thin pass-through layers, so these verify correct delegation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.responses import StreamingResponse

from src.controller.session_controller import SessionController
from src.controller.chat_controller import ChatController
from src.schemas.chat import ChatRequest
from tests.conftest import TEST_SESSION_ID


pytestmark = pytest.mark.unit



# ---------------------------------------------------------------------------
# SessionController
# ---------------------------------------------------------------------------
class TestSessionController:
    async def test_get_all_sessions(self):
        session_service = AsyncMock()
        session_service.list_sessions.return_value = []

        controller = SessionController(session_service)

        result = await controller.get_all_sessions(limit=10, offset=5)

        assert result == []
        session_service.list_sessions.assert_awaited_once_with(limit=10, offset=5)

    async def test_get_session(self):
        session_service = AsyncMock()
        session_service.get_session_detail.return_value = MagicMock()

        controller = SessionController(session_service)

        await controller.get_session(TEST_SESSION_ID, limit=25, offset=10)

        session_service.get_session_detail.assert_awaited_once_with(TEST_SESSION_ID, limit=25, offset=10)

    async def test_delete_session(self):
        session_service = AsyncMock()
        session_service.delete_session.return_value = None

        controller = SessionController(session_service)

        await controller.delete_session(TEST_SESSION_ID)

        session_service.delete_session.assert_awaited_once_with(TEST_SESSION_ID)


# ---------------------------------------------------------------------------
# ChatController
# ---------------------------------------------------------------------------
class TestChatController:
    async def test_handle_chat_stream_returns_streaming_response(self):
        chat_service = MagicMock()

        async def fake_generator():
            yield "data: test\n\n"

        chat_service.stream_chat_response.return_value = fake_generator()

        controller = ChatController(chat_service)
        request = ChatRequest(message="Hello")

        result = await controller.handle_chat_stream(request)

        assert isinstance(result, StreamingResponse)
        assert result.media_type == "text/event-stream"



