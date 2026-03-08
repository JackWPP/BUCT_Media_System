"""
Celery wrappers for AI analysis tasks.
"""
import asyncio

from app.core.celery_app import celery_app
from app.services.ai_tasks import run_ai_analysis_task


if celery_app is not None:
    @celery_app.task(name="app.tasks.ai.run_photo_ai_analysis")
    def run_photo_ai_analysis(task_id: str) -> None:
        asyncio.run(run_ai_analysis_task(task_id))
