"""
Unit tests for AuthService.
All external dependencies (user_repo, httpx/LiteLLM) are mocked.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from src.services.implementations.auth_service import AuthService
from src.schemas.user import UserResponse
from tests.conftest import TEST_USER_ID, TEST_USERNAME, TEST_API_KEY


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_service(user_repo=None, settings=None):
    if user_repo is None:
        user_repo = AsyncMock()
    if settings is None:
        settings = MagicMock()
        settings.LITELLM_URL = "http://litellm:4000"
        settings.LITELLM_MASTER_KEY = "sk-master"
        settings.DEFAULT_CODE_MODEL = "qwen-coder"
    return AuthService(user_repo, settings)


# ---------------------------------------------------------------------------
# authenticate_key
# ---------------------------------------------------------------------------
class TestAuthenticateKey:
    async def test_success(self, mock_user_entity):
        repo = AsyncMock()
        repo.get_by_api_key.return_value = mock_user_entity
        service = _build_service(user_repo=repo)

        result = await service.authenticate_key(TEST_API_KEY)

        assert result is mock_user_entity
        repo.get_by_api_key.assert_awaited_once_with(TEST_API_KEY)

    async def test_missing_key_raises_401(self):
        service = _build_service()

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_key("")
        assert exc_info.value.status_code == 401

    async def test_empty_none_key_raises_401(self):
        service = _build_service()

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_key(None)
        assert exc_info.value.status_code == 401

    async def test_invalid_key_raises_403(self):
        repo = AsyncMock()
        repo.get_by_api_key.return_value = None
        service = _build_service(user_repo=repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_key("bad-key")
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------
class TestGetCurrentUser:
    async def test_returns_mapped_schema(self, mock_user_entity):
        service = _build_service()

        result = await service.get_current_user(mock_user_entity)

        assert isinstance(result, UserResponse)
        assert result.id == TEST_USER_ID
        assert result.username == TEST_USERNAME
        assert result.api_key == TEST_API_KEY


# ---------------------------------------------------------------------------
# provision_user
# ---------------------------------------------------------------------------
class TestProvisionUser:
    @patch("src.services.implementations.auth_service.httpx.AsyncClient")
    async def test_success(self, mock_client_cls, mock_user_entity):
        # Mock httpx response from LiteLLM /key/generate
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "sk-generated-key"}

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client_instance

        repo = AsyncMock()
        repo.create.return_value = mock_user_entity
        service = _build_service(user_repo=repo)

        result = await service.provision_user(TEST_USERNAME)

        assert isinstance(result, UserResponse)
        repo.create.assert_awaited_once_with(username=TEST_USERNAME, api_key="sk-generated-key")

    @patch("src.services.implementations.auth_service.httpx.AsyncClient")
    async def test_litellm_failure_raises_500(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client_instance

        service = _build_service()

        with pytest.raises(HTTPException) as exc_info:
            await service.provision_user(TEST_USERNAME)
        assert exc_info.value.status_code == 500
