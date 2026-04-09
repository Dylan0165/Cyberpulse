"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "autopentest",
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
    task_routes={
        "app.workers.scan_tasks.*": {"queue": "scans"},
        "app.workers.analysis_tasks.*": {"queue": "analysis"},
    },
    beat_schedule={
        "cleanup-stale-containers": {
            "task": "app.workers.scan_tasks.cleanup_containers",
            "schedule": crontab(minute="*/15"),
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])
