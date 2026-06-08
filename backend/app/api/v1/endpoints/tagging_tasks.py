"""
Student tagging task endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.photos import serialize_photo
from app.core.deps import get_current_auditor_user, get_current_tagger_user, get_db
from app.crud import user as user_crud
from app.models.tagging_task import TaggingTask, TaggingTaskItem
from app.models.user import User
from app.schemas.user import User as UserSchema
from app.schemas.tagging_task import (
    TaggingTaskCreate,
    TaggingTaskBatchCreate,
    TaggingPhotoCandidateListResponse,
    TaggingTaskItemBatchReview,
    TaggingTaskItemDraft,
    TaggingTaskItemResponse,
    TaggingTaskItemReview,
    TaggingTaskItemSubmit,
    TaggingTaskListResponse,
    TaggingTaskResponse,
)
from app.services import tagging_tasks as tagging_service
from app.services.taxonomy import PHOTO_TYPE_COMPAT_VALUES

router = APIRouter()


def _can_access_task(user: User, task: TaggingTask) -> bool:
    return user.role in ("admin", "auditor") or task.assignee_id == user.id


def _can_submit_item(user: User, item: TaggingTaskItem) -> bool:
    return item.task.assignee_id == user.id


async def _serialize_item(db: AsyncSession, item: TaggingTaskItem) -> TaggingTaskItemResponse:
    data = TaggingTaskItemResponse(
        id=item.id,
        task_id=item.task_id,
        photo_id=item.photo_id,
        status=item.status,
        original_tags=item.original_tags,
        submitted_tags=item.submitted_tags,
        original_classifications=item.original_classifications,
        submitted_classifications=item.submitted_classifications,
        draft_tags=item.draft_tags,
        draft_classifications=item.draft_classifications,
        draft_note=item.draft_note,
        draft_saved_at=item.draft_saved_at,
        submitter_note=item.submitter_note,
        reviewer_id=item.reviewer_id,
        reviewer_note=item.reviewer_note,
        submitted_at=item.submitted_at,
        reviewed_at=item.reviewed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        photo=None,
    )
    if item.photo:
        data.photo = await serialize_photo(db, item.photo)
    return data


async def _serialize_task(db: AsyncSession, task: TaggingTask) -> TaggingTaskResponse:
    data = TaggingTaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        creator_id=task.creator_id,
        assignee_id=task.assignee_id,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        stats=tagging_service.task_stats(task),
        items=[],
    )
    data.items = [await _serialize_item(db, item) for item in task.items]
    return data


@router.get("", response_model=TaggingTaskListResponse)
async def list_tagging_tasks(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_tagger_user),
):
    limit = min(limit, 100)
    tasks, total = await tagging_service.list_tasks_for_user(db, current_user, skip=skip, limit=limit)
    return TaggingTaskListResponse(
        total=total,
        items=[await _serialize_task(db, task) for task in tasks],
    )


@router.get("/assignees", response_model=list[UserSchema])
async def list_tagging_assignees(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    users, _ = await user_crud.get_users(db, skip=0, limit=500)
    return [
        UserSchema.model_validate(user)
        for user in users
        if user.role in {"tagger", "auditor", "admin"} and user.is_active
    ]


@router.get("/photo-candidates", response_model=TaggingPhotoCandidateListResponse)
async def list_photo_candidates(
    selection_mode: str = "all",
    status: str | None = "approved",
    search: str | None = None,
    photo_type: str | None = None,
    facet_key: str | None = None,
    skip: int = 0,
    limit: int = 60,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    allowed_modes = {"all", "zero_tags", "missing_core", "missing_facet", "dependency_missing", "search", "selected"}
    if selection_mode not in allowed_modes:
        raise HTTPException(status_code=400, detail=f"selection_mode must be one of: {', '.join(sorted(allowed_modes))}")
    if selection_mode == "missing_facet" and not facet_key:
        raise HTTPException(status_code=400, detail="facet_key is required for missing_facet")
    if photo_type and photo_type not in PHOTO_TYPE_COMPAT_VALUES:
        raise HTTPException(status_code=400, detail="photo_type must be a known photo type")
    limit = min(limit, 120)
    try:
        photos, total = await tagging_service.list_photo_candidates(
            db,
            selection_mode=selection_mode,
            status=status,
            search=search,
            photo_type=photo_type,
            facet_key=facet_key,
            skip=skip,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TaggingPhotoCandidateListResponse(
        total=total,
        items=[await serialize_photo(db, photo) for photo in photos],
    )


@router.post("", response_model=TaggingTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_tagging_task(
    payload: TaggingTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    assignee = await user_crud.get_user_by_id(db, payload.assignee_id)
    if assignee is None or assignee.role not in {"tagger", "auditor", "admin"}:
        raise HTTPException(status_code=400, detail="Assignee must be a tagger, auditor, or admin")
    task = await tagging_service.create_task(
        db,
        creator=current_user,
        title=payload.title,
        description=payload.description,
        assignee_id=payload.assignee_id,
        photo_ids=payload.photo_ids,
    )
    return await _serialize_task(db, task)


@router.post("/batch", response_model=list[TaggingTaskResponse], status_code=status.HTTP_201_CREATED)
async def create_tagging_task_batch(
    payload: TaggingTaskBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    assignees = []
    for assignee_id in payload.assignee_ids:
        assignee = await user_crud.get_user_by_id(db, assignee_id)
        if assignee is None or assignee.role not in {"tagger", "auditor", "admin"}:
            raise HTTPException(status_code=400, detail="All assignees must be taggers, auditors, or admins")
        assignees.append(assignee)

    photo_ids = payload.photo_ids
    if payload.selection_mode == "missing_facet" and not payload.facet_key:
        raise HTTPException(status_code=400, detail="facet_key is required for missing_facet")
    if payload.selection_mode in {"manual", "selected"} and not photo_ids:
        raise HTTPException(status_code=400, detail="photo_ids is required for selected tasks")
    if not photo_ids or payload.selection_mode not in {"manual", "selected"}:
        try:
            photo_ids = await tagging_service.list_photo_candidate_ids(
                db,
                selection_mode=payload.selection_mode,
                status=payload.status,
                search=payload.search,
                photo_type=payload.photo_type,
                facet_key=payload.facet_key,
                max_photos=payload.max_photos,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not photo_ids:
        raise HTTPException(status_code=400, detail="No photos matched the assignment criteria")

    try:
        tasks = await tagging_service.create_evenly_distributed_tasks(
            db,
            creator=current_user,
            title=payload.title,
            description=payload.description,
            assignee_ids=[assignee.id for assignee in assignees],
            photo_ids=photo_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [await _serialize_task(db, task) for task in tasks]


@router.get("/{task_id}", response_model=TaggingTaskResponse)
async def get_tagging_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_tagger_user),
):
    task = await tagging_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not _can_access_task(current_user, task):
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    return await _serialize_task(db, task)


@router.post("/items/{item_id}/draft", response_model=TaggingTaskItemResponse)
async def save_tagging_item_draft(
    item_id: str,
    payload: TaggingTaskItemDraft,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_tagger_user),
):
    item = await tagging_service.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Task item not found")
    if not _can_submit_item(current_user, item):
        raise HTTPException(status_code=403, detail="Only the assignee can save this item")
    if item.status == "approved":
        raise HTTPException(status_code=400, detail="Approved items cannot be edited")
    try:
        item = await tagging_service.save_draft(db, item, payload.tags, payload.classifications, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _serialize_item(db, item)


@router.post("/items/{item_id}/submit", response_model=TaggingTaskItemResponse)
async def submit_tagging_item(
    item_id: str,
    payload: TaggingTaskItemSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_tagger_user),
):
    item = await tagging_service.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Task item not found")
    if not _can_submit_item(current_user, item):
        raise HTTPException(status_code=403, detail="Only the assignee can submit this item")
    if item.status == "approved":
        raise HTTPException(status_code=400, detail="Approved items cannot be resubmitted")
    try:
        item = await tagging_service.submit_item(db, item, payload.tags, payload.classifications, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _serialize_item(db, item)


@router.post("/items/batch-approve", response_model=list[TaggingTaskItemResponse])
async def batch_approve_tagging_items(
    payload: TaggingTaskItemBatchReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    try:
        items = await tagging_service.batch_approve_items(db, payload.item_ids, current_user, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [await _serialize_item(db, item) for item in items]


@router.post("/items/batch-reject", response_model=list[TaggingTaskItemResponse])
async def batch_reject_tagging_items(
    payload: TaggingTaskItemBatchReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    items = await tagging_service.batch_reject_items(db, payload.item_ids, current_user, payload.note)
    return [await _serialize_item(db, item) for item in items]


@router.post("/items/{item_id}/approve", response_model=TaggingTaskItemResponse)
async def approve_tagging_item(
    item_id: str,
    payload: TaggingTaskItemReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    item = await tagging_service.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Task item not found")
    if item.status != "submitted":
        raise HTTPException(status_code=400, detail="Only submitted items can be approved")
    try:
        item = await tagging_service.approve_item(db, item, current_user, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _serialize_item(db, item)


@router.post("/items/{item_id}/reject", response_model=TaggingTaskItemResponse)
async def reject_tagging_item(
    item_id: str,
    payload: TaggingTaskItemReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    item = await tagging_service.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Task item not found")
    if item.status != "submitted":
        raise HTTPException(status_code=400, detail="Only submitted items can be rejected")
    item = await tagging_service.reject_item(db, item, current_user, payload.note)
    return await _serialize_item(db, item)
