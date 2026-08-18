from src.services.interfaces.services import ITaskService
from src.models.entities import UserEntity
from src.schemas.task import CodeReviewRequest, TaskStatusResponse


class TaskController:
    def __init__(self, task_service: ITaskService):
        self._task_service = task_service

    async def submit_code_review(self, request: CodeReviewRequest, user: UserEntity) -> TaskStatusResponse:
        return await self._task_service.enqueue_code_review(request, user)

    async def check_task(self, task_id: str, user: UserEntity) -> TaskStatusResponse:
        return await self._task_service.get_task_status(task_id, user.id)