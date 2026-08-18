import logging
from celery import Celery
from celery.signals import task_success, task_failure
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    "ai_code_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    imports=["src.worker.tasks"]
)


def _sync_update_task_status(task_id: str, status: str, result: dict | None = None):
    """Synchronously update task status in Postgres (runs inside Celery worker thread)."""
    try:
        import psycopg2
        import json
        db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            "UPDATE async_tasks SET status = %s, result = %s, updated_at = NOW() WHERE id = %s",
            (status, json.dumps(result) if result else None, task_id)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        logger.error(f"Failed to sync task {task_id} status to DB: {exc}")


@task_success.connect
def on_task_success(sender=None, result=None, **kwargs):
    task_id = sender.request.id
    _sync_update_task_status(task_id, "SUCCESS", result if isinstance(result, dict) else {"info": str(result)})


@task_failure.connect
def on_task_failure(sender=None, exception=None, **kwargs):
    task_id = sender.request.id
    _sync_update_task_status(task_id, "FAILURE", {"error": str(exception)})