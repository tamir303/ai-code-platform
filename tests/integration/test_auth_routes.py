"""
Integration tests for authentication routes.
Tests POST /auth/provision and GET /auth/me through the full FastAPI stack.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from tests.conftest import TEST_USER_ID, TEST_USERNAME, TEST_API_KEY


pytestmark = pytest.mark.integration


class TestProvisionUser:
    @patch("src.services.implementations.auth_service.httpx.AsyncClient")
    async def test_provision_creates_user(self, mock_httpx_cls, authenticated_client, seeded_user):
        """POST /api/v1/auth/provision with mocked LiteLLM returns 201."""
        # Mock LiteLLM /key/generate
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "sk-new-key-for-newuser"}

        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_cls.return_value = mock_instance

        resp = await authenticated_client.post(
            "/api/v1/auth/provision",
            json={"username": "newuser"},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["api_key"] == "sk-new-key-for-newuser"
        assert "id" in data

    @patch("src.services.implementations.auth_service.httpx.AsyncClient")
    async def test_provision_litellm_failure(self, mock_httpx_cls, authenticated_client, seeded_user):
        """POST /api/v1/auth/provision when LiteLLM fails returns 500."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "LiteLLM error"

        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_cls.return_value = mock_instance

        resp = await authenticated_client.post(
            "/api/v1/auth/provision",
            json={"username": "failuser"},
        )

        assert resp.status_code == 500


class TestGetMe:
    async def test_get_me_authenticated(self, authenticated_client, seeded_user):
        """GET /api/v1/auth/me returns the authenticated user."""
        resp = await authenticated_client.get("/api/v1/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == TEST_USERNAME
        assert data["api_key"] == TEST_API_KEY

    async def test_get_me_with_real_auth_flow(self, client, seeded_user):
        """GET /api/v1/auth/me with a real X-API-Key header, no auth override —
        exercises the real AuthService.authenticate_key -> user_repo.get_by_api_key path."""
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"X-API-Key": TEST_API_KEY},
        )

        assert resp.status_code == 200
        assert resp.json()["username"] == TEST_USERNAME

    async def test_get_me_unauthenticated(self, client):
        """GET /api/v1/auth/me without API key returns 401 or 403."""
        resp = await client.get("/api/v1/auth/me")

        # FastAPI's APIKeyHeader with auto_error=False + our service raises 401
        assert resp.status_code in (401, 403)
