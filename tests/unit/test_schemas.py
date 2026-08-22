"""
Unit tests for Pydantic schemas validation.
"""
import uuid

import pytest
from pydantic import ValidationError

from src.schemas.chat import ChatRequest, ChatChunkResponse
from src.schemas.session import MessageItem, SessionResponse, SessionDetailResponse


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


