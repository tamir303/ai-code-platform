from uuid import UUID
from fastapi import HTTPException
from celery.result import AsyncResult
from src.services.interfaces.services import ITaskService
from src.db.interfaces.repositories import ITaskRepository
from src.models.entities import UserEntity
from src.schemas.task import CodeReviewRequest, TaskStatusResponse
from src.worker.tasks import batch_code_review_task


class TaskService(ITaskService):
    def __init__(self, task_repo: ITaskRepository):
        self._task_repo = task_repo

    async def enqueue_code_review(self, request: CodeReviewRequest, user: UserEntity) -> TaskStatusResponse:
        files_dict = [f.model_dump() for f in request.files]
        job = batch_code_review_task.delay(files_dict, user.api_key)
        
        await self._task_repo.create(task_id=job.id, user_id=user.id, task_type="BATCH_CODE_REVIEW")
        return TaskStatusResponse(task_id=job.id, status="QUEUED")

    async def get_task_status(self, task_id: str, user_id: UUID) -> TaskStatusResponse:
        record = await self._task_repo.get_by_id(task_id, user_id)
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")

        job = AsyncResult(task_id)
        current_status = job.status
        result = job.result if job.ready() else job.info

        # Sync back to DB if finished
        if current_status in ["SUCCESS", "FAILURE"]:
            await self._task_repo.update_status(task_id, current_status, result if isinstance(result, dict) else {"info": str(result)})

        return TaskStatusResponse(task_id=task_id, status=current_status, result=result if isinstance(result, dict) else None)