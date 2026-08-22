from fastapi.responses import StreamingResponse
from src.services.interfaces.services import IChatService
from src.schemas.chat import ChatRequest


class ChatController:
    def __init__(self, chat_service: IChatService):
        self._chat_service = chat_service

    async def handle_chat_stream(self, request: ChatRequest) -> StreamingResponse:
        generator = self._chat_service.stream_chat_response(request)
        return StreamingResponse(generator, media_type="text/event-stream")
