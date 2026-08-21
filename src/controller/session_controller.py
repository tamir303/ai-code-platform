from uuid import UUID
from src.services.interfaces.services import ISessionService
from src.models.entities import UserEntity
from src.schemas.session import SessionResponse, SessionDetailResponse


class SessionController:
    def __init__(self, session_service: ISessionService):
        self._session_service = session_service

    async def get_all_sessions(self, user: UserEntity, limit: int = 20, offset: int = 0) -> list[SessionResponse]:
        return await self._session_service.list_user_sessions(user.id, limit=limit, offset=offset)

    async def get_session(self, session_id: UUID, user: UserEntity, limit: int = 50, offset: int = 0) -> SessionDetailResponse:
        return await self._session_service.get_session_detail(session_id, user.id, limit=limit, offset=offset)

    async def delete_session(self, session_id: UUID, user: UserEntity) -> None:
        await self._session_service.delete_session(session_id, user.id)