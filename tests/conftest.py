"""
Shared test fixtures used across all test tiers (unit, integration, e2e).
"""
import uuid
from datetime import datetime, UTC

import pytest

from src.models.entities import SessionEntity, MessageEntity


# ---------------------------------------------------------------------------
# Deterministic IDs for reproducible tests
# ---------------------------------------------------------------------------
TEST_SESSION_ID = uuid.UUID("b2222222-2222-2222-2222-222222222222")
TEST_MESSAGE_ID = uuid.UUID("c3333333-3333-3333-3333-333333333333")

FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Entity fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_session_entity() -> SessionEntity:
    session = SessionEntity(
        id=TEST_SESSION_ID,
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
