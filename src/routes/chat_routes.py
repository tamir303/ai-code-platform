from fastapi import APIRouter, Depends
from src.schemas.chat import ChatRequest
from src.controller.chat_controller import ChatController
from src.di.container import get_chat_controller

router = APIRouter(prefix="/chat", tags=["Code Assistant Chat"])


@router.post("")
async def stream_chat(
    req: ChatRequest,
    controller: ChatController = Depends(get_chat_controller)
):
    """
    Initiates SSE streaming response for code questions or refactoring.
    Send: {"message": "..."} and optionally {"session_id": "..."} to continue
    an existing conversation.
    """
    return await controller.handle_chat_stream(req)
