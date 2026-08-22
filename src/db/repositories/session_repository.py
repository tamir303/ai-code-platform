from uuid import UUID
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.db.interfaces.repositories import ISessionRepository
from src.models.entities import SessionEntity, MessageEntity


class PostgresSessionRepository(ISessionRepository):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, title: str) -> SessionEntity:
        session = SessionEntity(title=title)
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def get_by_id(self, session_id: UUID) -> SessionEntity | None:
        stmt = (
            select(SessionEntity)
            .where(SessionEntity.id == session_id)
            .options(selectinload(SessionEntity.messages))
        )
        res = await self._db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(self, limit: int = 20, offset: int = 0) -> list[SessionEntity]:
        stmt = (
            select(SessionEntity)
            .order_by(SessionEntity.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await self._db.execute(stmt)
        return list(res.scalars().all())

    async def append_message(self, session_id: UUID, role: str, content: str) -> MessageEntity:
        msg = MessageEntity(session_id=session_id, role=role, content=content)
        self._db.add(msg)
        await self._db.commit()
        await self._db.refresh(msg)
        return msg

    async def get_messages(self, session_id: UUID, limit: int | None = None, offset: int = 0) -> list[MessageEntity]:
        stmt = (
            select(MessageEntity)
            .where(MessageEntity.session_id == session_id)
            .order_by(MessageEntity.created_at.asc())
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        res = await self._db.execute(stmt)
        return list(res.scalars().all())

    async def count_messages(self, session_id: UUID) -> int:
        stmt = select(func.count(MessageEntity.id)).where(MessageEntity.session_id == session_id)
        res = await self._db.execute(stmt)
        return res.scalar() or 0

    async def delete(self, session_id: UUID) -> bool:
        session = await self.get_by_id(session_id)
        if not session:
            return False
        await self._db.delete(session)
        await self._db.commit()
        return True
