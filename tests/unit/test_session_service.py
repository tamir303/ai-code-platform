"""
Unit tests for SessionService.
SessionRepository is fully mocked.
"""
import uuid

import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException

from src.services.implementations.session_service import SessionService
from src.schemas.session import SessionResponse, SessionDetailResponse
from tests.conftest import TEST_USER_ID, TEST_SESSION_ID, FIXED_NOW


pytestmark = pytest.mark.unit


def _build_service(session_repo=None):
    if session_repo is None:
        session_repo = AsyncMock()
    return SessionService(session_repo)


# ---------------------------------------------------------------------------
# list_user_sessions
# ---------------------------------------------------------------------------
class TestListUserSessions:
    async def test_returns_mapped_list(self, mock_session_entity):
        repo = AsyncMock()
        repo.list_by_user.return_value = [mock_session_entity]
        service = _build_service(session_repo=repo)

        result = await service.list_user_sessions(TEST_USER_ID, limit=10, offset=5)

        assert len(result) == 1
        assert isinstance(result[0], SessionResponse)
        assert result[0].id == TEST_SESSION_ID
        repo.list_by_user.assert_awaited_once_with(TEST_USER_ID, limit=10, offset=5)

    async def test_returns_empty_list(self):
        repo = AsyncMock()
        repo.list_by_user.return_value = []
        service = _build_service(session_repo=repo)

        result = await service.list_user_sessions(TEST_USER_ID)

        assert result == []
        repo.list_by_user.assert_awaited_once_with(TEST_USER_ID, limit=20, offset=0)


# ---------------------------------------------------------------------------
# get_session_detail
# ---------------------------------------------------------------------------
class TestGetSessionDetail:
    async def test_found(self, mock_session_entity, mock_message_entity):
        repo = AsyncMock()
        repo.get_by_id.return_value = mock_session_entity
        repo.get_messages.return_value = [mock_message_entity]
        repo.count_messages.return_value = 1
        service = _build_service(session_repo=repo)

        result = await service.get_session_detail(TEST_SESSION_ID, TEST_USER_ID, limit=10, offset=0)

        assert isinstance(result, SessionDetailResponse)
        assert result.id == TEST_SESSION_ID
        assert len(result.messages) == 1
        assert result.total_messages == 1
        assert result.limit == 10
        assert result.offset == 0
        repo.get_messages.assert_awaited_once_with(TEST_SESSION_ID, limit=10, offset=0)
        repo.count_messages.assert_awaited_once_with(TEST_SESSION_ID)

    async def test_not_found_raises_404(self):
        repo = AsyncMock()
        repo.get_by_id.return_value = None
        service = _build_service(session_repo=repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_session_detail(TEST_SESSION_ID, TEST_USER_ID)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------
class TestDeleteSession:
    async def test_success(self):
        repo = AsyncMock()
        repo.delete.return_value = True
        service = _build_service(session_repo=repo)

        # Should not raise
        await service.delete_session(TEST_SESSION_ID, TEST_USER_ID)

        repo.delete.assert_awaited_once_with(TEST_SESSION_ID, TEST_USER_ID)

    async def test_not_found_raises_404(self):
        repo = AsyncMock()
        repo.delete.return_value = False
        service = _build_service(session_repo=repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_session(TEST_SESSION_ID, TEST_USER_ID)
        assert exc_info.value.status_code == 404
