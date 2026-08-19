"""
Unit tests for AutocompleteService.
httpx (LiteLLM) calls are mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.implementations.autocomplete_service import AutocompleteService
from src.schemas.autocomplete import AutocompleteRequest


pytestmark = pytest.mark.unit


def _build_service(settings=None):
    if settings is None:
        settings = MagicMock()
        settings.LITELLM_URL = "http://litellm:4000"
        settings.DEFAULT_CODE_MODEL = "qwen-coder"
    return AutocompleteService(settings)


class TestGetCompletion:
    @patch("src.services.implementations.autocomplete_service.httpx.AsyncClient")
    async def test_builds_fim_prompt_and_returns_completion(self, mock_client_cls, mock_user_entity):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"choices": [{"text": "    return a + b"}]}

        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_instance

        service = _build_service()
        request = AutocompleteRequest(prefix="def add(a, b):\n", suffix="\n", language="python")

        result = await service.get_completion(request, mock_user_entity)

        assert result.completion == "    return a + b"

        call_kwargs = mock_instance.post.call_args.kwargs
        assert call_kwargs["json"]["prompt"] == "<|fim_prefix|>def add(a, b):\n<|fim_suffix|>\n<|fim_middle|>"
        assert call_kwargs["json"]["model"] == "qwen-coder"
        assert call_kwargs["headers"]["Authorization"] == f"Bearer {mock_user_entity.api_key}"

    @patch("src.services.implementations.autocomplete_service.httpx.AsyncClient")
    async def test_defaults_empty_suffix(self, mock_client_cls, mock_user_entity):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"choices": [{"text": "pass"}]}

        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_instance

        service = _build_service()
        request = AutocompleteRequest(prefix="def foo():\n")

        result = await service.get_completion(request, mock_user_entity)

        call_kwargs = mock_instance.post.call_args.kwargs
        assert call_kwargs["json"]["prompt"] == "<|fim_prefix|>def foo():\n<|fim_suffix|><|fim_middle|>"
        assert result.completion == "pass"
