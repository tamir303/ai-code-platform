from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.db.interfaces.repositories import ITaskRepository
from src.models.entities import TaskEntity


class PostgresTaskRepository(ITaskRepository):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, task_id: str, user_id: UUID, task_type: str) -> TaskEntity:
        task = TaskEntity(id=task_id, user_id=user_id, task_type=task_type, status="PENDING")
        self._db.add(task)
        await self._db.commit()
        await self._db.refresh(task)
        return task

    async def get_by_id(self, task_id: str, user_id: UUID) -> TaskEntity | None:
        stmt = select(TaskEntity).where(TaskEntity.id == task_id, TaskEntity.user_id == user_id)
        res = await self._db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_status(self, task_id: str, status: str, result: dict | None = None) -> None:
        stmt = select(TaskEntity).where(TaskEntity.id == task_id)
        res = await self._db.execute(stmt)
        task = res.scalar_one_or_none()
        if task:
            task.status = status
            if result:
                task.result = result
            await self._db.commit()