"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "cyberpulse",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.max_scan_duration_seconds,
    task_soft_time_limit=settings.max_scan_duration_seconds - 300,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Explicitly route tasks to the right queues
    task_routes={
        "app.workers.scan_tasks.*":     {"queue": "scans"},
        "app.workers.analysis_tasks.*": {"queue": "analysis"},
    },
    # Explicitly include the task modules so they are always imported by the worker.
    # autodiscover_tasks(["app.workers"]) only looks for app/workers/tasks.py
    # which doesn't exist — this is the correct way for non-standard filenames.
    include=[
        "app.workers.scan_tasks",
        "app.workers.analysis_tasks",
    ],
    beat_schedule={
        "cleanup-stale-containers": {
            "task": "app.workers.scan_tasks.cleanup_containers",
            "schedule": crontab(minute="*/15"),
        },
        "run-scheduled-scans": {
            "task": "app.workers.scan_tasks.run_scheduled_scans",
            "schedule": crontab(minute="*/15"),
        },
    },
)
