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


def _mock_client(mock_client_cls, completion_text):
    """Wire a mocked httpx.AsyncClient returning one /v1/completions payload."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"text": completion_text}]}

    mock_instance = AsyncMock()
    mock_instance.post.return_value = mock_response
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_instance
    return mock_instance


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


class TestCompletionBoundary:
    """
    A fill-in-the-middle completion must stop at the end of the hole it fills.
    Without stop tokens the model keeps generating past the fill and returns
    whole unrelated functions until it hits max_tokens — this is the exact
    output observed from a live Qwen2.5-Coder-0.5B-Instruct run.
    """

    # Verbatim capture from the live vLLM stack for the FIM prompt
    # "<|fim_prefix|>def add(a: int, b: int) -> int:\n    <|fim_suffix|>\n<|fim_middle|>"
    RUNAWAY = (
        "return a + b\n"
        "\n"
        "def subtract(a: int, b: int) -> int:\n"
        "    return a - b\n"
        "\n"
        "def multiply(a: int, b: int) -> int:\n"
        "    return a * b\n"
    )

    @patch("src.services.implementations.autocomplete_service.httpx.AsyncClient")
    async def test_stops_at_end_of_the_filled_block(self, mock_client_cls, mock_user_entity):
        _mock_client(mock_client_cls, self.RUNAWAY)

        result = await _build_service().get_completion(
            AutocompleteRequest(prefix="def add(a: int, b: int) -> int:\n    ", suffix="\n"),
            mock_user_entity,
        )

        assert result.completion == "return a + b"

    @patch("src.services.implementations.autocomplete_service.httpx.AsyncClient")
    async def test_requests_fim_stop_tokens(self, mock_client_cls, mock_user_entity):
        mock_instance = _mock_client(mock_client_cls, "pass")

        await _build_service().get_completion(
            AutocompleteRequest(prefix="def foo():\n    "), mock_user_entity
        )

        stop = mock_instance.post.call_args.kwargs["json"]["stop"]
        assert "<|fim_prefix|>" in stop
        assert "<|fim_suffix|>" in stop
        assert "<|fim_pad|>" in stop
        assert "<|endoftext|>" in stop

    @patch("src.services.implementations.autocomplete_service.httpx.AsyncClient")
    async def test_strips_leaked_special_tokens(self, mock_client_cls, mock_user_entity):
        _mock_client(mock_client_cls, "return a + b<|endoftext|>")

        result = await _build_service().get_completion(
            AutocompleteRequest(prefix="def add(a, b):\n    "), mock_user_entity
        )

        assert result.completion == "return a + b"

    @patch("src.services.implementations.autocomplete_service.httpx.AsyncClient")
    async def test_keeps_contiguous_multi_line_body(self, mock_client_cls, mock_user_entity):
        """Trimming must not truncate a legitimate multi-line fill."""
        _mock_client(mock_client_cls, "if b == 0:\n        raise ValueError('nope')\n    return a / b")

        result = await _build_service().get_completion(
            AutocompleteRequest(prefix="def div(a, b):\n    "), mock_user_entity
        )

        assert result.completion == "if b == 0:\n        raise ValueError('nope')\n    return a / b"
