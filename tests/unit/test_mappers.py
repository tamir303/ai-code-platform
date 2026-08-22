"""
Unit tests for EntityMapper utility.
"""
import pytest

from src.utils.mappers import EntityMapper
from src.schemas.session import SessionResponse, SessionDetailResponse, MessageItem
from tests.conftest import TEST_SESSION_ID, TEST_MESSAGE_ID, FIXED_NOW


pytestmark = pytest.mark.unit



class TestSessionEntityToSummary:
    def test_maps_summary_fields(self, mock_session_entity):
        result = EntityMapper.session_entity_to_summary(mock_session_entity)

        assert isinstance(result, SessionResponse)
        assert result.id == TEST_SESSION_ID
        assert result.title == "Test Session"
        assert result.created_at == FIXED_NOW
        assert result.updated_at == FIXED_NOW


class TestSessionEntityToDetail:
    def test_maps_with_empty_messages(self, mock_session_entity):
        result = EntityMapper.session_entity_to_detail(mock_session_entity)

        assert isinstance(result, SessionDetailResponse)
        assert result.id == TEST_SESSION_ID
        assert result.messages == []
        assert result.total_messages == 0
        assert result.limit == 50
        assert result.offset == 0

    def test_maps_with_messages(self, mock_session_entity, mock_message_entity):
        mock_session_entity.messages = [mock_message_entity]

        result = EntityMapper.session_entity_to_detail(mock_session_entity)

        assert len(result.messages) == 1
        assert isinstance(result.messages[0], MessageItem)
        assert result.messages[0].role == "user"
        assert result.messages[0].content == "Hello, world!"
        assert result.messages[0].created_at == FIXED_NOW
        assert result.total_messages == 1

    def test_maps_with_explicit_pagination_params(self, mock_session_entity, mock_message_entity):
        result = EntityMapper.session_entity_to_detail(
            entity=mock_session_entity,
            messages=[mock_message_entity],
            total_messages=100,
            limit=10,
            offset=20,
        )

        assert len(result.messages) == 1
        assert result.total_messages == 100
        assert result.limit == 10
        assert result.offset == 20
