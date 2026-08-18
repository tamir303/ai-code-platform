from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.db.interfaces.repositories import IUserRepository
from src.models.entities import UserEntity


class PostgresUserRepository(IUserRepository):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_api_key(self, api_key: str) -> UserEntity | None:
        stmt = select(UserEntity).where(UserEntity.api_key == api_key)
        res = await self._db.execute(stmt)
        return res.scalar_one_or_none()

    async def create(self, username: str, api_key: str) -> UserEntity:
        user = UserEntity(username=username, api_key=api_key)
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        return user