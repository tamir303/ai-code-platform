from uuid import UUID
from fastapi import HTTPException
from src.services.interfaces.services import ISessionService
from src.db.interfaces.repositories import ISessionRepository
from src.schemas.session import SessionResponse, SessionDetailResponse
from src.utils.mappers import EntityMapper


class SessionService(ISessionService):
    def __init__(self, session_repo: ISessionRepository):
        self._session_repo = session_repo

    async def list_sessions(self, limit: int = 20, offset: int = 0) -> list[SessionResponse]:
        entities = await self._session_repo.list_all(limit=limit, offset=offset)
        return [EntityMapper.session_entity_to_summary(e) for e in entities]

    async def get_session_detail(self, session_id: UUID, limit: int = 50, offset: int = 0) -> SessionDetailResponse:
        session = await self._session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        messages = await self._session_repo.get_messages(session_id, limit=limit, offset=offset)
        total_messages = await self._session_repo.count_messages(session_id)
        return EntityMapper.session_entity_to_detail(
            entity=session,
            messages=messages,
            total_messages=total_messages,
            limit=limit,
            offset=offset,
        )

    async def delete_session(self, session_id: UUID) -> None:
        deleted = await self._session_repo.delete(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
