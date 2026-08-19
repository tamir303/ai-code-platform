"""
Unit tests for app-level wiring in main.py: lifespan startup/shutdown and the
global exception handler. Called directly rather than through a live ASGI
request, since ASGITransport doesn't trigger lifespan events by default.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.main import app, lifespan, global_exception_handler


pytestmark = pytest.mark.unit


class TestLifespan:
    async def test_startup_and_shutdown(self):
        with patch("src.main.async_engine") as mock_engine:
            mock_engine.dispose = AsyncMock()
            async with lifespan(app):
                pass
            mock_engine.dispose.assert_awaited_once()


class TestGlobalExceptionHandler:
    async def test_returns_500_json(self):
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/boom"

        response = await global_exception_handler(mock_request, RuntimeError("kaboom"))

        assert response.status_code == 500
        assert response.body == b'{"detail":"Internal server error"}'
