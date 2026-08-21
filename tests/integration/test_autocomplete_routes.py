"""
Integration tests for the autocomplete route.
LiteLLM is mocked at the network boundary; DB is in-memory SQLite (unused by this route).
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


pytestmark = pytest.mark.integration


class TestAutocomplete:
    @patch("src.services.implementations.autocomplete_service.httpx.AsyncClient")
    async def test_returns_completion(self, mock_client_cls, authenticated_client, seeded_user):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"choices": [{"text": "    return a + b"}]}

        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_instance

        resp = await authenticated_client.post(
            "/api/v1/autocomplete",
            json={"prefix": "def add(a, b):\n", "suffix": "\n", "language": "python"},
        )

        assert resp.status_code == 200
        assert resp.json()["completion"] == "    return a + b"

    async def test_requires_prefix(self, authenticated_client, seeded_user):
        resp = await authenticated_client.post("/api/v1/autocomplete", json={})

        assert resp.status_code == 422

    async def test_unauthenticated_rejected(self, client):
        resp = await client.post(
            "/api/v1/autocomplete",
            json={"prefix": "def add(a, b):\n"},
        )

        assert resp.status_code in (401, 403)
