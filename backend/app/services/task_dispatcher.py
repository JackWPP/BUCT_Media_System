"""
Task dispatch helpers.
"""
from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.core.celery_app import celery_app
from app.services.ai_tasks import run_ai_analysis_task

settings = get_settings()


def dispatch_ai_analysis_task(background_tasks: BackgroundTasks, task_id: str) -> None:
    """Dispatch AI analysis using the configured backend."""
    if settings.TASK_QUEUE_BACKEND == "celery" and celery_app is not None:
        celery_app.send_task("app.tasks.ai.run_photo_ai_analysis", args=[task_id])
        return
    background_tasks.add_task(run_ai_analysis_task, task_id)
