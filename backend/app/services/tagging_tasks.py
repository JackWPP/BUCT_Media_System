"""
Student tagging task workflow helpers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud import photo as photo_crud
from app.crud import tag as tag_crud
from app.models.photo import Photo
from app.models.tag import PhotoTag, Tag
from app.models.taxonomy import PhotoClassification, TaxonomyFacet, TaxonomyNode
from app.models.tagging_task import TaggingTask, TaggingTaskItem
from app.models.user import User
from app.services.taxonomy import get_node_by_id, serialize_classifications, set_photo_classifications


def _is_reviewer(user: User) -> bool:
    return user.role in ("admin", "auditor")


def _item_photo_load():
    return selectinload(TaggingTaskItem.photo).options(
        selectinload(Photo.classifications).selectinload(PhotoClassification.facet),
        selectinload(Photo.classifications).selectinload(PhotoClassification.node),
        selectinload(Photo.tags),
    )


async def get_task(db: AsyncSession, task_id: str) -> TaggingTask | None:
    result = await db.execute(
        select(TaggingTask)
        .options(selectinload(TaggingTask.items).options(_item_photo_load()))
        .where(TaggingTask.id == task_id)
    )
    return result.scalar_one_or_none()


async def get_item(db: AsyncSession, item_id: str) -> TaggingTaskItem | None:
    result = await db.execute(
        select(TaggingTaskItem)
        .options(
            selectinload(TaggingTaskItem.task),
            _item_photo_load(),
        )
        .where(TaggingTaskItem.id == item_id)
    )
    return result.scalar_one_or_none()


async def list_tasks_for_user(
    db: AsyncSession,
    user: User,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[TaggingTask], int]:
    query = select(TaggingTask).options(
        selectinload(TaggingTask.items).options(_item_photo_load())
    )
    count_query = select(func.count(TaggingTask.id))
    if not _is_reviewer(user):
        query = query.where(TaggingTask.assignee_id == user.id)
        count_query = count_query.where(TaggingTask.assignee_id == user.id)
    query = query.order_by(TaggingTask.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    count_result = await db.execute(count_query)
    return list(result.scalars().all()), count_result.scalar_one()


async def create_task(
    db: AsyncSession,
    creator: User,
    title: str,
    description: str | None,
    assignee_id: str,
    photo_ids: Iterable[str],
) -> TaggingTask:
    task = TaggingTask(
        title=title,
        description=description,
        creator_id=creator.id,
        assignee_id=assignee_id,
        status="pending",
    )
    db.add(task)
    await db.flush()

    seen: set[str] = set()
    for photo_id in photo_ids:
        if photo_id in seen:
            continue
        seen.add(photo_id)
        db.add(TaggingTaskItem(task_id=task.id, photo_id=photo_id, status="pending"))

    await db.commit()
    return await get_task(db, task.id)


def _photo_candidate_query(
    selection_mode: str = "all",
    status: str | None = "approved",
    search: str | None = None,
    photo_type: str | None = None,
):
    query = select(Photo)
    count_query = select(func.count(Photo.id.distinct()))

    if status:
        query = query.where(Photo.status == status)
        count_query = count_query.where(Photo.status == status)

    if selection_mode == "zero_tags":
        tag_exists = select(PhotoTag.photo_id).where(PhotoTag.photo_id == Photo.id).exists()
        query = query.where(~tag_exists)
        count_query = count_query.where(~tag_exists)

    if photo_type:
        legacy_categories = {
            "风光类": ("Landscape", "风光", "风光类"),
            "纪实类": ("Documentary", "Activity", "纪实", "活动", "纪实类"),
            "校园风光": ("Landscape", "风光", "风光类", "校园风光"),
            "人文纪实": ("Documentary", "Activity", "纪实", "活动", "纪实类", "人文纪实"),
            "自然生态": ("Landscape", "自然生态"),
        }.get(photo_type, ())
        type_subquery = (
            select(PhotoClassification.photo_id)
            .join(TaxonomyFacet, TaxonomyFacet.id == PhotoClassification.facet_id)
            .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
            .where(
                TaxonomyFacet.key == "photo_type",
                TaxonomyFacet.is_active.is_(True),
                TaxonomyNode.is_active.is_(True),
                TaxonomyNode.name == photo_type,
            )
        )
        type_filter = Photo.id.in_(type_subquery)
        if legacy_categories:
            type_filter = or_(type_filter, Photo.category.in_(legacy_categories))
        query = query.where(type_filter)
        count_query = count_query.where(type_filter)

    if search:
        pattern = f"%{search}%"
        tag_subquery = select(PhotoTag.photo_id).join(Tag).where(Tag.name.ilike(pattern))
        search_filter = or_(
            Photo.filename.ilike(pattern),
            Photo.description.ilike(pattern),
            Photo.id.in_(tag_subquery),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    return query, count_query


async def list_photo_candidates(
    db: AsyncSession,
    selection_mode: str = "all",
    status: str | None = "approved",
    search: str | None = None,
    photo_type: str | None = None,
    skip: int = 0,
    limit: int = 60,
) -> tuple[list[Photo], int]:
    query, count_query = _photo_candidate_query(selection_mode, status, search, photo_type)
    result = await db.execute(
        query.options(
            selectinload(Photo.classifications).selectinload(PhotoClassification.facet),
            selectinload(Photo.classifications).selectinload(PhotoClassification.node),
            selectinload(Photo.tags),
        )
        .order_by(Photo.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    count_result = await db.execute(count_query)
    return list(result.scalars().all()), count_result.scalar_one()


async def list_photo_candidate_ids(
    db: AsyncSession,
    selection_mode: str,
    status: str | None,
    search: str | None,
    photo_type: str | None,
    max_photos: int,
) -> list[str]:
    query, _ = _photo_candidate_query(selection_mode, status, search, photo_type)
    result = await db.execute(query.with_only_columns(Photo.id).order_by(Photo.created_at.desc()).limit(max_photos))
    return list(result.scalars().all())


async def create_evenly_distributed_tasks(
    db: AsyncSession,
    creator: User,
    title: str,
    description: str | None,
    assignee_ids: list[str],
    photo_ids: Iterable[str],
) -> list[TaggingTask]:
    unique_photo_ids = list(dict.fromkeys(photo_ids))
    if not unique_photo_ids:
        raise ValueError("No photos selected")
    if not assignee_ids:
        raise ValueError("No assignees selected")

    buckets = {assignee_id: [] for assignee_id in assignee_ids}
    for index, photo_id in enumerate(unique_photo_ids):
        assignee_id = assignee_ids[index % len(assignee_ids)]
        buckets[assignee_id].append(photo_id)

    tasks: list[TaggingTask] = []
    for index, assignee_id in enumerate(assignee_ids, start=1):
        bucket = buckets[assignee_id]
        if not bucket:
            continue
        task_title = title if len(assignee_ids) == 1 else f"{title} - 第{index}组"
        task = TaggingTask(
            title=task_title,
            description=description,
            creator_id=creator.id,
            assignee_id=assignee_id,
            status="pending",
        )
        db.add(task)
        await db.flush()
        for photo_id in bucket:
            db.add(TaggingTaskItem(task_id=task.id, photo_id=photo_id, status="pending"))
        tasks.append(task)

    await db.commit()
    hydrated: list[TaggingTask] = []
    for task in tasks:
        loaded = await get_task(db, task.id)
        if loaded:
            hydrated.append(loaded)
    return hydrated


async def submit_item(
    db: AsyncSession,
    item: TaggingTaskItem,
    tag_names: list[str],
    classifications: dict[str, int | list[int]],
    note: str | None,
) -> TaggingTaskItem:
    photo = await photo_crud.get_photo_with_tags(db, item.photo_id)
    if photo is None:
        raise ValueError("Photo not found")

    submitted_classifications = {}
    for facet_key, value in classifications.items():
        node_ids = value if isinstance(value, list) else [value]
        nodes_payload = []
        for node_id in node_ids:
            node = await get_node_by_id(db, int(node_id))
            if node is None or not node.is_active:
                raise ValueError(f"Unknown node id: {node_id}")
            nodes_payload.append({"node_id": node.id, "node_name": node.name})
        if isinstance(value, list):
            submitted_classifications[facet_key] = {
                "node_ids": [node["node_id"] for node in nodes_payload],
                "nodes": nodes_payload,
            }
        elif nodes_payload:
            submitted_classifications[facet_key] = nodes_payload[0]

    item.original_tags = [tag.name for tag in await photo_crud.get_photo_tags(db, photo.id)]
    item.original_classifications = serialize_classifications(photo)
    item.submitted_tags = tag_names
    item.submitted_classifications = submitted_classifications
    item.submitter_note = note
    item.status = "submitted"
    item.submitted_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    item.task.status = "in_progress"
    await db.commit()
    return await get_item(db, item.id)


async def approve_item(
    db: AsyncSession,
    item: TaggingTaskItem,
    reviewer: User,
    note: str | None,
) -> TaggingTaskItem:
    photo = await photo_crud.get_photo_with_tags(db, item.photo_id)
    if photo is None:
        raise ValueError("Photo not found")

    tag_ids = []
    for tag_name in item.submitted_tags or []:
        tag = await tag_crud.get_or_create_tag(db, tag_name)
        tag_ids.append(tag.id)
    await photo_crud.add_tags_to_photo(db, photo.id, tag_ids)

    classification_ids = {}
    for facet_key, value in (item.submitted_classifications or {}).items():
        if not value:
            continue
        if value.get("node_ids"):
            classification_ids[facet_key] = [int(node_id) for node_id in value["node_ids"]]
        elif value.get("node_id"):
            classification_ids[facet_key] = int(value["node_id"])
    if classification_ids:
        await set_photo_classifications(db, photo, classification_ids)

    item.status = "approved"
    item.reviewer_id = reviewer.id
    item.reviewer_note = note
    item.reviewed_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    await _refresh_task_status(db, item.task)
    await db.commit()
    return await get_item(db, item.id)


async def reject_item(
    db: AsyncSession,
    item: TaggingTaskItem,
    reviewer: User,
    note: str | None,
) -> TaggingTaskItem:
    item.status = "rejected"
    item.reviewer_id = reviewer.id
    item.reviewer_note = note
    item.reviewed_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    await _refresh_task_status(db, item.task)
    await db.commit()
    return await get_item(db, item.id)


async def _refresh_task_status(db: AsyncSession, task: TaggingTask) -> None:
    result = await db.execute(select(TaggingTaskItem.status).where(TaggingTaskItem.task_id == task.id))
    statuses = [row[0] for row in result.all()]
    if statuses and all(status in {"approved", "rejected"} for status in statuses):
        task.status = "completed"
        task.completed_at = datetime.utcnow()
    elif any(status == "submitted" for status in statuses):
        task.status = "reviewing"
    elif any(status != "pending" for status in statuses):
        task.status = "in_progress"
    else:
        task.status = "pending"
    task.updated_at = datetime.utcnow()
