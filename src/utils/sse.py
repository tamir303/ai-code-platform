import json


def format_sse_event(data: dict, event: str | None = None) -> str:
    """Encodes a Python dictionary into an SSE line payload."""
    payload = f"data: {json.dumps(data)}\n\n"
    if event:
        payload = f"event: {event}\n" + payload
    return payload