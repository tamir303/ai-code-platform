"""
Unit tests for the batch_code_review Celery task.
Run via .apply() (Celery's always-eager synchronous execution) so no broker
is needed. httpx.Client (sync) is mocked.
"""
import pytest
from unittest.mock import MagicMock, patch

from src.worker.tasks import batch_code_review_task


pytestmark = pytest.mark.unit


class TestBatchCodeReviewTask:
    @pytest.fixture(autouse=True)
    def _isolate_from_broker_and_db(self):
        """
        Keep these as true unit tests with no broker/DB running:
          - the task is bind=True and calls self.update_state(state="PROGRESS", ...),
            which writes to the real Celery result backend (Redis) even under .apply();
          - completing the task fires Celery's task_success signal, whose handler
            opens a real psycopg2 connection to Postgres (swallowed on failure,
            but it still blocks ~3s per test on connection timeout).
        """
        with patch.object(batch_code_review_task, "update_state"), \
                patch("src.worker.celery_app._sync_update_task_status"):
            yield

    @patch("src.worker.tasks.httpx.Client")
    def test_success(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Looks fine."}}]
        }
        mock_instance = MagicMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = False
        mock_client_cls.return_value = mock_instance

        files = [{"filename": "a.py", "code": "print(1)"}]
        result = batch_code_review_task.apply(args=[files, "sk-test"]).get()

        assert result["status"] == "COMPLETED"
        assert result["files_analyzed"][0]["status"] == "success"
        assert result["files_analyzed"][0]["review"] == "Looks fine."

    @patch("src.worker.tasks.httpx.Client")
    def test_http_failure(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "server error"
        mock_instance = MagicMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = False
        mock_client_cls.return_value = mock_instance

        files = [{"filename": "b.py", "code": "print(2)"}]
        result = batch_code_review_task.apply(args=[files, "sk-test"]).get()

        assert result["files_analyzed"][0]["status"] == "failed"
        assert result["files_analyzed"][0]["error"] == "server error"

    @patch("src.worker.tasks.httpx.Client")
    def test_client_exception(self, mock_client_cls):
        mock_client_cls.side_effect = RuntimeError("connection refused")

        files = [{"filename": "c.py", "code": "print(3)"}]
        result = batch_code_review_task.apply(args=[files, "sk-test"]).get()

        assert result["files_analyzed"][0]["status"] == "error"
        assert "connection refused" in result["files_analyzed"][0]["error"]

    @patch("src.worker.tasks.httpx.Client")
    def test_multiple_files_progress_tracked(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_instance = MagicMock()
        mock_instance.post.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = False
        mock_client_cls.return_value = mock_instance

        files = [
            {"filename": "a.py", "code": "pass"},
            {"filename": "b.py", "code": "pass"},
        ]
        result = batch_code_review_task.apply(args=[files, "sk-test"]).get()

        assert len(result["files_analyzed"]) == 2
        assert mock_instance.post.call_count == 2
