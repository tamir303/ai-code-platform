"""
Unit tests for TaskService.
TaskRepository and Celery are mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.services.implementations.task_service import TaskService
from src.schemas.task import CodeReviewRequest, CodeFilePayload, TaskStatusResponse
from tests.conftest import TEST_USER_ID, TEST_TASK_ID


pytestmark = pytest.mark.unit


def _build_service(task_repo=None):
    if task_repo is None:
        task_repo = AsyncMock()
    return TaskService(task_repo)


# ---------------------------------------------------------------------------
# enqueue_code_review
# ---------------------------------------------------------------------------
class TestEnqueueCodeReview:
    @patch("src.services.implementations.task_service.batch_code_review_task")
    async def test_success(self, mock_celery_task, mock_user_entity):
        mock_job = MagicMock()
        mock_job.id = TEST_TASK_ID
        mock_celery_task.delay.return_value = mock_job

        repo = AsyncMock()
        repo.create.return_value = MagicMock(id=TEST_TASK_ID)
        service = _build_service(task_repo=repo)

        request = CodeReviewRequest(
            files=[CodeFilePayload(filename="main.py", code="print('hi')")]
        )
        result = await service.enqueue_code_review(request, mock_user_entity)

        assert isinstance(result, TaskStatusResponse)
        assert result.task_id == TEST_TASK_ID
        assert result.status == "QUEUED"
        mock_celery_task.delay.assert_called_once()
        repo.create.assert_awaited_once_with(
            task_id=TEST_TASK_ID,
            user_id=mock_user_entity.id,
            task_type="BATCH_CODE_REVIEW"
        )


# ---------------------------------------------------------------------------
# get_task_status
# ---------------------------------------------------------------------------
class TestGetTaskStatus:
    @patch("src.services.implementations.task_service.AsyncResult")
    async def test_found_pending(self, mock_async_result_cls, mock_task_entity):
        repo = AsyncMock()
        repo.get_by_id.return_value = mock_task_entity

        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_result.ready.return_value = False
        mock_result.info = None
        mock_async_result_cls.return_value = mock_result

        service = _build_service(task_repo=repo)

        result = await service.get_task_status(TEST_TASK_ID, TEST_USER_ID)

        assert isinstance(result, TaskStatusResponse)
        assert result.task_id == TEST_TASK_ID
        assert result.status == "PENDING"

    async def test_not_found_raises_404(self):
        repo = AsyncMock()
        repo.get_by_id.return_value = None
        service = _build_service(task_repo=repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_task_status(TEST_TASK_ID, TEST_USER_ID)
        assert exc_info.value.status_code == 404

    @patch("src.services.implementations.task_service.AsyncResult")
    async def test_syncs_finished_status_to_db(self, mock_async_result_cls, mock_task_entity):
        repo = AsyncMock()
        repo.get_by_id.return_value = mock_task_entity

        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.ready.return_value = True
        mock_result.result = {"status": "COMPLETED", "files_analyzed": []}
        mock_async_result_cls.return_value = mock_result

        service = _build_service(task_repo=repo)

        result = await service.get_task_status(TEST_TASK_ID, TEST_USER_ID)

        assert result.status == "SUCCESS"
        repo.update_status.assert_awaited_once_with(
            TEST_TASK_ID,
            "SUCCESS",
            {"status": "COMPLETED", "files_analyzed": []}
        )

    @patch("src.services.implementations.task_service.AsyncResult")
    async def test_failure_status_synced(self, mock_async_result_cls, mock_task_entity):
        repo = AsyncMock()
        repo.get_by_id.return_value = mock_task_entity

        mock_result = MagicMock()
        mock_result.status = "FAILURE"
        mock_result.ready.return_value = True
        mock_result.result = "Some error"  # Not a dict
        mock_async_result_cls.return_value = mock_result

        service = _build_service(task_repo=repo)

        result = await service.get_task_status(TEST_TASK_ID, TEST_USER_ID)

        assert result.status == "FAILURE"
        # Non-dict results get wrapped
        repo.update_status.assert_awaited_once_with(
            TEST_TASK_ID,
            "FAILURE",
            {"info": "Some error"}
        )
