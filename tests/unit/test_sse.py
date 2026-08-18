"""
Unit tests for SSE utility function.
"""
import json

import pytest

from src.utils.sse import format_sse_event


pytestmark = pytest.mark.unit


class TestFormatSSEEvent:
    def test_basic_data_event(self):
        data = {"content": "hello", "is_done": False}
        result = format_sse_event(data)

        assert result.startswith("data: ")
        assert result.endswith("\n\n")

        # Parse the JSON payload
        json_str = result[len("data: "):-2]
        parsed = json.loads(json_str)
        assert parsed["content"] == "hello"
        assert parsed["is_done"] is False

    def test_event_with_name(self):
        data = {"content": "done"}
        result = format_sse_event(data, event="completion")

        assert result.startswith("event: completion\n")
        assert "data: " in result
        assert result.endswith("\n\n")

    def test_empty_dict(self):
        result = format_sse_event({})

        json_str = result[len("data: "):-2]
        parsed = json.loads(json_str)
        assert parsed == {}

    def test_nested_data(self):
        data = {"session_id": "abc-123", "meta": {"key": "value"}}
        result = format_sse_event(data)

        json_str = result[len("data: "):-2]
        parsed = json.loads(json_str)
        assert parsed["meta"]["key"] == "value"
