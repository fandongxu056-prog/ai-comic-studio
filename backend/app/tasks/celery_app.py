"""Celery application configuration for async task processing."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "ai_comic_studio",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.image_tasks",
        "app.tasks.video_tasks",
        "app.tasks.tts_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,   # 10 min soft limit
    task_time_limit=900,        # 15 min hard limit
)
