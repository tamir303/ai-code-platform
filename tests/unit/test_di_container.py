"""
Unit tests for DI wiring functions that aren't exercised through overridden
test fixtures (e.g. get_db_session, which every integration/e2e fixture overrides).
"""
import pytest
from unittest.mock import AsyncMock, patch

from src.di.container import get_db_session


pytestmark = pytest.mark.unit


class TestGetDbSession:
    @patch("src.di.container.AsyncSessionLocal")
    async def test_yields_session_from_session_local(self, mock_session_local):
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_context.__aexit__.return_value = False
        mock_session_local.return_value = mock_context

        gen = get_db_session()
        yielded = await gen.__anext__()
        assert yielded is mock_session

        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

        mock_context.__aexit__.assert_awaited_once()
