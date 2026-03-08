"""
Celery application for optional task queue dispatching.
"""
from app.core.config import get_settings

settings = get_settings()

try:
    from celery import Celery
except ModuleNotFoundError:  # pragma: no cover - optional dependency for local mode
    Celery = None


if Celery is not None:
    celery_app = Celery(
        "buct_media",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )
    celery_app.conf.task_default_queue = "buct_media"
else:
    celery_app = None
