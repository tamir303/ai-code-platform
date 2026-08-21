"""
Shared test fixtures used across all test tiers (unit, integration, e2e).
"""
import uuid
from datetime import datetime, UTC

import pytest

from src.models.entities import UserEntity, SessionEntity, MessageEntity


# ---------------------------------------------------------------------------
# Deterministic IDs for reproducible tests
# ---------------------------------------------------------------------------
TEST_USER_ID = uuid.UUID("a1111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = uuid.UUID("b2222222-2222-2222-2222-222222222222")
TEST_MESSAGE_ID = uuid.UUID("c3333333-3333-3333-3333-333333333333")
TEST_API_KEY = "sk-test-key-abc123"
TEST_USERNAME = "testuser"

FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Entity fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_user_entity() -> UserEntity:
    user = UserEntity(
        id=TEST_USER_ID,
        username=TEST_USERNAME,
        api_key=TEST_API_KEY,
        created_at=FIXED_NOW,
    )
    user.sessions = []
    return user


@pytest.fixture
def mock_session_entity(mock_user_entity) -> SessionEntity:
    session = SessionEntity(
        id=TEST_SESSION_ID,
        user_id=mock_user_entity.id,
        title="Test Session",
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
    )
    session.messages = []
    return session


@pytest.fixture
def mock_message_entity(mock_session_entity) -> MessageEntity:
    msg = MessageEntity(
        id=TEST_MESSAGE_ID,
        session_id=mock_session_entity.id,
        role="user",
        content="Hello, world!",
        created_at=FIXED_NOW,
    )
    return msg
