from abc import ABC, abstractmethod
from typing import AsyncGenerator
from uuid import UUID
from src.schemas.chat import ChatRequest
from src.schemas.session import SessionResponse, SessionDetailResponse


class ISessionService(ABC):
    @abstractmethod
    async def list_sessions(self, limit: int = 20, offset: int = 0) -> list[SessionResponse]: ...
    @abstractmethod
    async def get_session_detail(self, session_id: UUID, limit: int = 50, offset: int = 0) -> SessionDetailResponse: ...
    @abstractmethod
    async def delete_session(self, session_id: UUID) -> None: ...


class IChatService(ABC):
    @abstractmethod
    async def stream_chat_response(self, request: ChatRequest) -> AsyncGenerator[str, None]: ...
