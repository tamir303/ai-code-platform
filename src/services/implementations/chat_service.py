import json
from typing import AsyncGenerator
from uuid import UUID
import httpx
from src.services.interfaces.services import IChatService
from src.db.interfaces.repositories import ISessionRepository
from src.schemas.chat import ChatRequest
from src.config.settings import AppSettings
from src.utils.sse import format_sse_event


class ChatService(IChatService):
    def __init__(self, session_repo: ISessionRepository, settings: AppSettings):
        self._session_repo = session_repo
        self._settings = settings

    async def stream_chat_response(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        # 1. Resolve or Create Session automatically
        session_id: UUID
        if request.session_id:
            existing = await self._session_repo.get_by_id(request.session_id)
            if not existing:
                # Auto-heal by creating new if missing
                auto_title = request.message[:35] + ("..." if len(request.message) > 35 else "")
                new_session = await self._session_repo.create(auto_title)
                session_id = new_session.id
            else:
                session_id = existing.id
        else:
            auto_title = request.message[:35] + ("..." if len(request.message) > 35 else "")
            new_session = await self._session_repo.create(auto_title)
            session_id = new_session.id

        # 2. Append User Message
        await self._session_repo.append_message(session_id, "user", request.message)

        # 3. Build Full Context Window
        past_msgs = await self._session_repo.get_messages(session_id)
        llm_messages = [{"role": "system", "content": self._settings.SYSTEM_PROMPT}]
        for m in past_msgs:
            llm_messages.append({"role": m.role, "content": m.content})

        # 4. Stream from LiteLLM / vLLM
        accumulated_bot_response = []
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._settings.LITELLM_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._settings.LITELLM_MASTER_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self._settings.DEFAULT_CODE_MODEL,
                    "messages": llm_messages,
                    "stream": True,
                    "temperature": 0.1
                }
            ) as response:
                async for chunk in response.aiter_lines():
                    if not chunk or not chunk.startswith("data: "):
                        continue
                    payload = chunk[6:].strip()
                    if payload == "[DONE]":
                        break
                    
                    try:
                        parsed = json.loads(payload)
                        delta = parsed["choices"][0]["delta"].get("content", "")
                        if delta:
                            accumulated_bot_response.append(delta)
                            # Emit SSE chunk to client
                            yield format_sse_event({
                                "session_id": str(session_id),
                                "content": delta,
                                "is_done": False
                            })
                    except Exception:
                        continue

        # 5. Persist the Assistant's full answer to Postgres
        full_text = "".join(accumulated_bot_response)
        if full_text:
            await self._session_repo.append_message(session_id, "assistant", full_text)

        # 6. Send final SSE completion signal
        yield format_sse_event({
            "session_id": str(session_id),
            "content": "",
            "is_done": True
        })