"""
Unit tests for Pydantic schemas validation.
"""
import uuid

import pytest
from pydantic import ValidationError

from src.schemas.chat import ChatRequest, ChatChunkResponse
from src.schemas.user import UserCreateRequest, UserResponse
from src.schemas.session import MessageItem, SessionResponse, SessionDetailResponse
from src.schemas.autocomplete import AutocompleteRequest, AutocompleteResponse


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ChatRequest
# ---------------------------------------------------------------------------
class TestChatRequest:
    def test_valid_without_session_id(self):
        req = ChatRequest(message="Hello AI")
        assert req.message == "Hello AI"
        assert req.session_id is None

    def test_valid_with_session_id(self):
        sid = uuid.uuid4()
        req = ChatRequest(message="Hello", session_id=sid)
        assert req.session_id == sid

    def test_missing_message_raises(self):
        with pytest.raises(ValidationError):
            ChatRequest()


class TestChatChunkResponse:
    def test_valid(self):
        sid = uuid.uuid4()
        chunk = ChatChunkResponse(session_id=sid, content="hello")
        assert chunk.is_done is False

    def test_done_flag(self):
        sid = uuid.uuid4()
        chunk = ChatChunkResponse(session_id=sid, content="", is_done=True)
        assert chunk.is_done is True



# ---------------------------------------------------------------------------
# UserCreateRequest / UserResponse
# ---------------------------------------------------------------------------
class TestUserCreateRequest:
    def test_valid(self):
        req = UserCreateRequest(username="alice")
        assert req.username == "alice"

    def test_missing_username_raises(self):
        with pytest.raises(ValidationError):
            UserCreateRequest()


class TestUserResponse:
    def test_valid(self):
        uid = uuid.uuid4()
        resp = UserResponse(id=uid, username="bob", api_key="sk-abc")
        assert resp.id == uid



# ---------------------------------------------------------------------------
# Session schemas
# ---------------------------------------------------------------------------
class TestSessionSchemas:
    def test_session_response(self):
        from datetime import datetime, UTC
        now = datetime.now(UTC)
        resp = SessionResponse(id=uuid.uuid4(), title="Test", created_at=now, updated_at=now)
        assert resp.title == "Test"

    def test_session_detail_response_default_messages(self):
        from datetime import datetime, UTC
        now = datetime.now(UTC)
        resp = SessionDetailResponse(id=uuid.uuid4(), title="Test", created_at=now, updated_at=now)
        assert resp.messages == []
        assert resp.total_messages == 0
        assert resp.limit == 50
        assert resp.offset == 0


# ---------------------------------------------------------------------------
# Autocomplete schemas
# ---------------------------------------------------------------------------
class TestAutocompleteRequest:
    def test_valid_with_all_fields(self):
        req = AutocompleteRequest(prefix="def add(a, b):\n    ", suffix="\n", language="python")
        assert req.prefix == "def add(a, b):\n    "
        assert req.suffix == "\n"
        assert req.language == "python"

    def test_suffix_and_language_default(self):
        req = AutocompleteRequest(prefix="def add(a, b):\n    ")
        assert req.suffix == ""
        assert req.language is None

    def test_missing_prefix_raises(self):
        with pytest.raises(ValidationError):
            AutocompleteRequest()


class TestAutocompleteResponse:
    def test_valid(self):
        resp = AutocompleteResponse(completion="return a + b")
        assert resp.completion == "return a + b"
