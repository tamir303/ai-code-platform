from abc import ABC, abstractmethod
from typing import AsyncGenerator
from uuid import UUID
from src.schemas.chat import ChatRequest
from src.schemas.session import SessionResponse, SessionDetailResponse
from src.schemas.user import UserResponse
from src.schemas.autocomplete import AutocompleteRequest, AutocompleteResponse
from src.models.entities import UserEntity


class IAuthService(ABC):
    @abstractmethod
    async def authenticate_key(self, api_key: str) -> UserEntity: ...
    @abstractmethod
    async def provision_user(self, username: str) -> UserResponse: ...
    @abstractmethod
    async def get_current_user(self, user: UserEntity) -> UserResponse: ...


class ISessionService(ABC):
    @abstractmethod
    async def list_user_sessions(self, user_id: UUID, limit: int = 20, offset: int = 0) -> list[SessionResponse]: ...
    @abstractmethod
    async def get_session_detail(self, session_id: UUID, user_id: UUID, limit: int = 50, offset: int = 0) -> SessionDetailResponse: ...
    @abstractmethod
    async def delete_session(self, session_id: UUID, user_id: UUID) -> None: ...


class IChatService(ABC):
    @abstractmethod
    async def stream_chat_response(
        self, request: ChatRequest, user: UserEntity
    ) -> AsyncGenerator[str, None]: ...


class IAutocompleteService(ABC):
    @abstractmethod
    async def get_completion(self, request: AutocompleteRequest, user: UserEntity) -> AutocompleteResponse: ...