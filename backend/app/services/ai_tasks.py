"""
Persisted AI task lifecycle helpers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.crud import photo as photo_crud
from app.crud import tag as tag_crud
from app.models.ai_analysis import AIAnalysisTask
from app.models.photo import Photo
from app.services.ai_tagging import analyze_photo_with_runtime_settings
from app.services.runtime_settings import get_runtime_settings
from app.services.storage import get_storage
from app.services.taxonomy import resolve_taxonomy_node, set_photo_classification


async def create_ai_analysis_task(
    db: AsyncSession,
    photo: Photo,
    requested_by_id: Optional[str],
    provider: str,
    model_id: str,
) -> AIAnalysisTask:
    task = AIAnalysisTask(
        photo_id=photo.id,
        requested_by_id=requested_by_id,
        provider=provider,
        model_id=model_id,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_ai_task(db: AsyncSession, task_id: str) -> Optional[AIAnalysisTask]:
    result = await db.execute(select(AIAnalysisTask).where(AIAnalysisTask.id == task_id))
    return result.scalar_one_or_none()


async def get_latest_ai_task_for_photo(db: AsyncSession, photo_id: str) -> Optional[AIAnalysisTask]:
    result = await db.execute(
        select(AIAnalysisTask)
        .where(AIAnalysisTask.photo_id == photo_id)
        .order_by(AIAnalysisTask.created_at.desc())
    )
    return result.scalars().first()


async def run_ai_analysis_task(task_id: str) -> Optional[AIAnalysisTask]:
    storage = get_storage()
    async with AsyncSessionLocal() as db:
        task = await get_ai_task(db, task_id)
        if task is None:
            return None

        photo = await photo_crud.get_photo(db, task.photo_id)
        if photo is None:
            task.status = "failed"
            task.error_message = "Photo not found."
            task.updated_at = datetime.utcnow()
            await db.commit()
            return task

        task.status = "processing"
        task.updated_at = datetime.utcnow()
        await db.commit()

        try:
            runtime_settings = await get_runtime_settings(db)
            with storage.local_copy(photo.original_path) as local_path:
                result = await analyze_photo_with_runtime_settings(
                    local_path,
                    providers=runtime_settings.providers,
                    enabled=runtime_settings.ai_enabled,
                )

            if result is None:
                task.status = "failed"
                task.error_message = "AI analysis returned no result."
                photo.processing_status = "failed"
            else:
                task.status = "completed"
                task.result_json = result
                task.provider = result.get("provider", task.provider)
                task.model_id = result.get("model_id", task.model_id)
                task.completed_at = datetime.utcnow()
                photo.processing_status = "completed"
        except Exception as exc:  # noqa: BLE001
            task.status = "failed"
            task.error_message = str(exc)
            photo.processing_status = "failed"

        task.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(task)
        return task


async def apply_ai_analysis_task(
    db: AsyncSession,
    task: AIAnalysisTask,
    reviewer_id: str,
) -> dict[str, str]:
    unresolved: dict[str, str] = {}
    if not task.result_json:
        return unresolved

    photo = await photo_crud.get_photo_with_tags(db, task.photo_id)
    if photo is None:
        raise ValueError("Photo not found.")

    classifications = (task.result_json or {}).get("classifications") or {}
    for facet_key, raw_value in classifications.items():
        if not raw_value:
            continue
        node = await resolve_taxonomy_node(db, facet_key, str(raw_value))
        if node is None:
            unresolved[facet_key] = str(raw_value)
            continue
        await set_photo_classification(db, photo, facet_key, node)

    suggested_tags = (task.result_json or {}).get("free_tags") or []
    existing_tags = [tag.name for tag in await photo_crud.get_photo_tags(db, photo.id)]
    merged_tag_names = list(dict.fromkeys(existing_tags + [str(tag).strip() for tag in suggested_tags if str(tag).strip()]))

    if merged_tag_names:
        tag_ids: list[int] = []
        for tag_name in merged_tag_names:
            tag = await tag_crud.get_or_create_tag(db, tag_name)
            tag_ids.append(tag.id)
        await photo_crud.add_tags_to_photo(db, photo.id, tag_ids)

    task.status = "applied"
    task.reviewed_by_id = reviewer_id
    task.applied_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)
    return unresolved
