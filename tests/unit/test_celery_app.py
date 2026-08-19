"""
Unit tests for Celery signal handlers and the synchronous DB-sync helper
in src/worker/celery_app.py. psycopg2 is mocked — no real Postgres needed.
"""
import pytest
from unittest.mock import MagicMock, patch

from src.worker.celery_app import _sync_update_task_status, on_task_success, on_task_failure


pytestmark = pytest.mark.unit


class TestSyncUpdateTaskStatus:
    @patch("psycopg2.connect")
    def test_updates_row_with_result(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        _sync_update_task_status("task-1", "SUCCESS", {"status": "COMPLETED"})

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("psycopg2.connect")
    def test_updates_row_without_result(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        _sync_update_task_status("task-2", "FAILURE", None)

        args, _ = mock_cursor.execute.call_args
        assert args[1][1] is None

    @patch("psycopg2.connect")
    def test_logs_error_on_db_failure(self, mock_connect):
        mock_connect.side_effect = RuntimeError("db down")

        # Should not raise - the failure path only logs
        _sync_update_task_status("task-3", "SUCCESS", {"x": 1})


class TestSignalHandlers:
    @patch("src.worker.celery_app._sync_update_task_status")
    def test_on_task_success_syncs_dict_result(self, mock_sync):
        sender = MagicMock()
        sender.request.id = "task-4"

        on_task_success(sender=sender, result={"status": "COMPLETED"})

        mock_sync.assert_called_once_with("task-4", "SUCCESS", {"status": "COMPLETED"})

    @patch("src.worker.celery_app._sync_update_task_status")
    def test_on_task_success_wraps_non_dict_result(self, mock_sync):
        sender = MagicMock()
        sender.request.id = "task-5"

        on_task_success(sender=sender, result="plain string")

        mock_sync.assert_called_once_with("task-5", "SUCCESS", {"info": "plain string"})

    @patch("src.worker.celery_app._sync_update_task_status")
    def test_on_task_failure_syncs_error(self, mock_sync):
        sender = MagicMock()
        sender.request.id = "task-6"

        on_task_failure(sender=sender, exception=ValueError("boom"))

        mock_sync.assert_called_once_with("task-6", "FAILURE", {"error": "boom"})
