from fastapi import APIRouter, Depends
from src.schemas.task import CodeReviewRequest, TaskStatusResponse
from src.controller.task_controller import TaskController
from src.di.container import get_task_controller, get_authenticated_user
from src.models.entities import UserEntity

router = APIRouter(prefix="/tasks", tags=["Async Jobs & Celery"])


@router.post("/code-review", response_model=TaskStatusResponse)
async def create_code_review_task(
    req: CodeReviewRequest,
    user: UserEntity = Depends(get_authenticated_user),
    controller: TaskController = Depends(get_task_controller)
):
    return await controller.submit_code_review(req, user)


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    user: UserEntity = Depends(get_authenticated_user),
    controller: TaskController = Depends(get_task_controller)
):
    return await controller.check_task(task_id, user)