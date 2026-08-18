from fastapi import APIRouter, Depends
from src.schemas.chat import ChatRequest
from src.controller.chat_controller import ChatController
from src.di.container import get_chat_controller, get_authenticated_user
from src.models.entities import UserEntity

router = APIRouter(prefix="/chat", tags=["Code Assistant Chat"])


@router.post("")
async def stream_chat(
    req: ChatRequest,
    user: UserEntity = Depends(get_authenticated_user),
    controller: ChatController = Depends(get_chat_controller)
):
    """
    Initiates SSE streaming response for code questions or refactoring.
    User only needs to send: {"message": "..."}
    """
    return await controller.handle_chat_stream(req, user)