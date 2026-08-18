from uuid import UUID
from fastapi import HTTPException
from src.services.interfaces.services import ISessionService
from src.db.interfaces.repositories import ISessionRepository
from src.schemas.session import SessionResponse, SessionDetailResponse
from src.utils.mappers import EntityMapper


class SessionService(ISessionService):
    def __init__(self, session_repo: ISessionRepository):
        self._session_repo = session_repo

    async def list_user_sessions(self, user_id: UUID) -> list[SessionResponse]:
        entities = await self._session_repo.list_by_user(user_id)
        return [EntityMapper.session_entity_to_summary(e) for e in entities]

    async def get_session_detail(self, session_id: UUID, user_id: UUID) -> SessionDetailResponse:
        session = await self._session_repo.get_by_id(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return EntityMapper.session_entity_to_detail(session)

    async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
        deleted = await self._session_repo.delete(session_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")