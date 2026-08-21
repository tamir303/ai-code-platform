"""
Unit tests for all controllers.
Controllers are thin pass-through layers, so these verify correct delegation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.responses import StreamingResponse

from src.controller.auth_controller import AuthController
from src.controller.session_controller import SessionController
from src.controller.chat_controller import ChatController
from src.controller.autocomplete_controller import AutocompleteController
from src.schemas.autocomplete import AutocompleteRequest, AutocompleteResponse
from src.schemas.user import UserCreateRequest, UserResponse
from src.schemas.chat import ChatRequest
from tests.conftest import TEST_USER_ID, TEST_SESSION_ID, TEST_API_KEY, TEST_USERNAME


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# AuthController
# ---------------------------------------------------------------------------
class TestAuthController:
    async def test_register_user_delegates(self):
        auth_service = AsyncMock()
        expected = UserResponse(id=TEST_USER_ID, username=TEST_USERNAME, api_key=TEST_API_KEY)
        auth_service.provision_user.return_value = expected

        controller = AuthController(auth_service)
        request = UserCreateRequest(username=TEST_USERNAME)

        result = await controller.register_user(request)

        assert result == expected
        auth_service.provision_user.assert_awaited_once_with(TEST_USERNAME)

    async def test_get_me_delegates(self, mock_user_entity):
        auth_service = AsyncMock()
        expected = UserResponse(id=TEST_USER_ID, username=TEST_USERNAME, api_key=TEST_API_KEY)
        auth_service.get_current_user.return_value = expected

        controller = AuthController(auth_service)

        result = await controller.get_me(mock_user_entity)

        assert result == expected
        auth_service.get_current_user.assert_awaited_once_with(mock_user_entity)


# ---------------------------------------------------------------------------
# SessionController
# ---------------------------------------------------------------------------
class TestSessionController:
    async def test_get_all_sessions(self, mock_user_entity):
        session_service = AsyncMock()
        session_service.list_user_sessions.return_value = []

        controller = SessionController(session_service)

        result = await controller.get_all_sessions(mock_user_entity, limit=10, offset=5)

        assert result == []
        session_service.list_user_sessions.assert_awaited_once_with(mock_user_entity.id, limit=10, offset=5)

    async def test_get_session(self, mock_user_entity):
        session_service = AsyncMock()
        session_service.get_session_detail.return_value = MagicMock()

        controller = SessionController(session_service)

        await controller.get_session(TEST_SESSION_ID, mock_user_entity, limit=25, offset=10)

        session_service.get_session_detail.assert_awaited_once_with(TEST_SESSION_ID, mock_user_entity.id, limit=25, offset=10)

    async def test_delete_session(self, mock_user_entity):
        session_service = AsyncMock()
        session_service.delete_session.return_value = None

        controller = SessionController(session_service)

        await controller.delete_session(TEST_SESSION_ID, mock_user_entity)

        session_service.delete_session.assert_awaited_once_with(TEST_SESSION_ID, mock_user_entity.id)


# ---------------------------------------------------------------------------
# ChatController
# ---------------------------------------------------------------------------
class TestChatController:
    async def test_handle_chat_stream_returns_streaming_response(self, mock_user_entity):
        chat_service = MagicMock()

        async def fake_generator():
            yield "data: test\n\n"

        chat_service.stream_chat_response.return_value = fake_generator()

        controller = ChatController(chat_service)
        request = ChatRequest(message="Hello")

        result = await controller.handle_chat_stream(request, mock_user_entity)

        assert isinstance(result, StreamingResponse)
        assert result.media_type == "text/event-stream"



# ---------------------------------------------------------------------------
# AutocompleteController
# ---------------------------------------------------------------------------
class TestAutocompleteController:
    async def test_handle_autocomplete_delegates(self, mock_user_entity):
        autocomplete_service = AsyncMock()
        expected = AutocompleteResponse(completion="return a + b")
        autocomplete_service.get_completion.return_value = expected

        controller = AutocompleteController(autocomplete_service)
        request = AutocompleteRequest(prefix="def add(a, b):\n    ")

        result = await controller.handle_autocomplete(request, mock_user_entity)

        assert result == expected
        autocomplete_service.get_completion.assert_awaited_once_with(request, mock_user_entity)
