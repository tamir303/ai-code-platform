"""
Integration tests for task routes.
Celery task dispatch is mocked; DB operations use in-memory SQLite.
"""
import pytest
from unittest.mock import patch, MagicMock

from src.models.entities import TaskEntity
from tests.conftest import TEST_USER_ID, TEST_TASK_ID, FIXED_NOW
from tests.integration.conftest import TestSessionLocal


pytestmark = pytest.mark.integration


async def _seed_task():
    """Insert a task directly into the test DB."""
    async with TestSessionLocal() as session:
        entity = TaskEntity(
            id=TEST_TASK_ID,
            user_id=TEST_USER_ID,
            task_type="BATCH_CODE_REVIEW",
            status="PENDING",
            created_at=FIXED_NOW,
            updated_at=FIXED_NOW,
        )
        session.add(entity)
        await session.commit()
        return entity


class TestCreateCodeReview:
    @patch("src.services.implementations.task_service.batch_code_review_task")
    async def test_enqueue_success(self, mock_celery_task, authenticated_client, seeded_user):
        """POST /api/v1/tasks/code-review enqueues and returns task ID."""
        mock_job = MagicMock()
        mock_job.id = TEST_TASK_ID
        mock_celery_task.delay.return_value = mock_job

        resp = await authenticated_client.post(
            "/api/v1/tasks/code-review",
            json={
                "files": [
                    {"filename": "main.py", "code": "print('hello')"},
                    {"filename": "utils.py", "code": "def add(a, b): return a + b"},
                ]
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == TEST_TASK_ID
        assert data["status"] == "QUEUED"

    @patch("src.services.implementations.task_service.batch_code_review_task")
    async def test_enqueue_empty_files(self, mock_celery_task, authenticated_client, seeded_user):
        """POST /api/v1/tasks/code-review with empty files still succeeds."""
        mock_job = MagicMock()
        mock_job.id = "task-empty"
        mock_celery_task.delay.return_value = mock_job

        resp = await authenticated_client.post(
            "/api/v1/tasks/code-review",
            json={"files": []},
        )

        assert resp.status_code == 200


class TestGetTaskStatus:
    @patch("src.services.implementations.task_service.AsyncResult")
    async def test_found(self, mock_async_result_cls, authenticated_client, seeded_user):
        """GET /api/v1/tasks/{id} returns task status."""
        await _seed_task()

        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_result.ready.return_value = False
        mock_result.info = None
        mock_async_result_cls.return_value = mock_result

        resp = await authenticated_client.get(f"/api/v1/tasks/{TEST_TASK_ID}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == TEST_TASK_ID
        assert data["status"] == "PENDING"

    async def test_not_found(self, authenticated_client, seeded_user):
        """GET /api/v1/tasks/{id} with nonexistent task returns 404."""
        resp = await authenticated_client.get("/api/v1/tasks/nonexistent-task-id")

        assert resp.status_code == 404
