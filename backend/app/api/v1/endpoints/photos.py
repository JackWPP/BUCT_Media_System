"""
Photo API endpoints.
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import (
    get_current_admin_user,
    get_current_auditor_user,
    get_current_user,
    get_db,
    get_optional_current_user,
    get_optional_current_user_for_media,
    get_portrait_visibility,
)
from app.crud import permission as permission_crud
from app.crud import photo as photo_crud
from app.crud import tag as tag_crud
from app.models.ai_analysis import AIAnalysisTask
from app.models.photo import Photo
from app.models.system_config import PortraitVisibility
from app.models.user import User
from app.schemas.ai_analysis import AIAnalysisTaskCreate, AIAnalysisTaskResponse, AIApplyResponse
from app.schemas.photo import PhotoListResponse, PhotoResponse, PhotoUpdate, PhotoUploadResponse
from app.schemas.search import SearchInterpretRequest, SearchInterpretResponse
from app.schemas.taxonomy import PhotoClassificationUpdateSchema
from app.services.ai_tasks import (
    apply_ai_analysis_task,
    create_ai_analysis_task,
    get_ai_task,
    get_latest_ai_task_for_photo,
)
from app.services.image_processing import process_uploaded_image
from app.services.runtime_settings import get_runtime_settings
from app.services.search_interpreter import get_search_interpreter
from app.services.storage import cleanup_staged_files, get_storage, stage_photo_upload
from app.services.task_dispatcher import dispatch_ai_analysis_task
from app.services.taxonomy import ensure_default_taxonomy, serialize_classifications
from app.services.audit import log_audit
from app.services.notification import notify_user as send_notification

settings = get_settings()
router = APIRouter()


def is_reviewer(user: Optional[User]) -> bool:
    return bool(user and user.role in ("admin", "auditor"))


async def can_access_portrait_photo(
    db: AsyncSession,
    current_user: Optional[User],
    portrait_visibility: str,
) -> bool:
    if portrait_visibility == PortraitVisibility.PUBLIC:
        return True
    if not current_user:
        return False
    if portrait_visibility == PortraitVisibility.LOGIN_REQUIRED:
        return True
    return await permission_crud.check_permission(db, current_user.id, "category", "Portrait", "view")


async def can_access_photo_publicly(
    db: AsyncSession,
    photo: Photo,
    current_user: Optional[User],
    portrait_visibility: str,
) -> bool:
    if photo.status != "approved":
        return False
    if photo.category != "Portrait":
        return True
    return await can_access_portrait_photo(db, current_user, portrait_visibility)


def _photo_free_tags(tags: list) -> list[str]:
    return [tag.name for tag in tags]


async def serialize_photo(db: AsyncSession, photo: Photo) -> PhotoResponse:
    tags = await photo_crud.get_photo_tags(db, photo.id)
    free_tags = _photo_free_tags(tags)
    photo_dict = {**photo.__dict__}
    photo_dict.pop("_sa_instance_state", None)
    photo_dict["tags"] = free_tags
    photo_dict["free_tags"] = free_tags
    photo_dict["classifications"] = serialize_classifications(photo)
    photo_dict["uploader_name"] = None
    return PhotoResponse(**photo_dict)


async def serialize_photos(db: AsyncSession, photos: List[Photo]) -> List[PhotoResponse]:
    return [await serialize_photo(db, photo) for photo in photos]


async def _assert_photo_access(
    db: AsyncSession,
    photo: Photo,
    current_user: Optional[User],
    portrait_visibility: str,
) -> None:
    can_access = (
        is_reviewer(current_user)
        or (current_user and photo.uploader_id == current_user.id)
        or await can_access_photo_publicly(db, photo, current_user, portrait_visibility)
    )
    if not can_access:
        raise HTTPException(status_code=404, detail="Photo not found")


@router.get("/public", response_model=PhotoListResponse)
async def list_public_photos(
    skip: int = 0,
    limit: int = 20,
    season: Optional[str] = None,
    category: Optional[str] = None,
    campus: Optional[str] = None,
    building: Optional[str] = None,
    gallery_series: Optional[str] = None,
    gallery_year: Optional[str] = None,
    photo_type: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    smart: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    portrait_visibility: str = Depends(get_portrait_visibility),
):
    limit = min(limit, 100)
    if sort_by not in ["created_at", "views", "published_at"]:
        sort_by = "created_at"
    if sort_order not in ["asc", "desc"]:
        sort_order = "desc"

    should_filter_portrait = False
    if portrait_visibility == PortraitVisibility.LOGIN_REQUIRED and not current_user:
        should_filter_portrait = True
    elif portrait_visibility == PortraitVisibility.AUTHORIZED_ONLY:
        if not current_user or not await can_access_portrait_photo(db, current_user, portrait_visibility):
            should_filter_portrait = True

    interpretation = None
    search_interpretation_data = None

    if smart and search:
        runtime_settings = await get_runtime_settings(db)
        if runtime_settings.ai_search_enabled:
            interpreter = get_search_interpreter()
            interpretation = await interpreter.interpret(search, db)
            search_interpretation_data = {
                "facet_filters": interpretation.facet_filters,
                "keywords": interpretation.keywords,
                "original_query": interpretation.original_query,
                "method": interpretation.method,
                "confidence": interpretation.confidence,
                "explanation": interpretation.explanation,
            }
        else:
            smart = False

    photos, total = await photo_crud.get_photos(
        db,
        skip=skip,
        limit=limit,
        status="approved",
        season=season,
        category=category,
        campus=campus,
        building=building,
        gallery_series=gallery_series,
        gallery_year=gallery_year,
        photo_type=photo_type,
        search=search if not interpretation else None,
        tag=tag,
        exclude_categories=["Portrait"] if should_filter_portrait else None,
        sort_by=sort_by,
        sort_order=sort_order,
        interpretation=interpretation,
    )
    return PhotoListResponse(
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
        items=await serialize_photos(db, photos),
        search_interpretation=search_interpretation_data,
    )


@router.post("/interpret-search", response_model=SearchInterpretResponse)
async def interpret_search(
    payload: SearchInterpretRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    interpreter = get_search_interpreter()
    result = await interpreter.interpret(payload.query, db)
    return SearchInterpretResponse(
        facet_filters=result.facet_filters,
        keywords=result.keywords,
        original_query=result.original_query,
        method=result.method,
        confidence=result.confidence,
        explanation=result.explanation,
    )


@router.get("/public/{photo_id}", response_model=PhotoResponse)
async def get_public_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    portrait_visibility: str = Depends(get_portrait_visibility),
):
    photo = await photo_crud.get_photo_with_tags(db, photo_id)
    if not photo or not await can_access_photo_publicly(db, photo, current_user, portrait_visibility):
        raise HTTPException(status_code=404, detail="Photo not found")
    return await serialize_photo(db, photo)


@router.get("/{photo_id}/image/original")
async def get_photo_image(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user_for_media),
    portrait_visibility: str = Depends(get_portrait_visibility),
):
    photo = await photo_crud.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    await _assert_photo_access(db, photo, current_user, portrait_visibility)
    return get_storage().build_media_response(photo.original_path)


@router.get("/{photo_id}/image/thumbnail")
async def get_photo_thumbnail(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user_for_media),
    portrait_visibility: str = Depends(get_portrait_visibility),
):
    photo = await photo_crud.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    await _assert_photo_access(db, photo, current_user, portrait_visibility)
    # Fall back to original if no thumbnail exists
    path = photo.thumb_path or photo.original_path
    return get_storage().build_media_response(path)


@router.get("/{photo_id}/download")
async def download_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user_for_media),
    portrait_visibility: str = Depends(get_portrait_visibility),
):
    photo = await photo_crud.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    await _assert_photo_access(db, photo, current_user, portrait_visibility)
    return get_storage().build_media_response(photo.original_path, download_name=photo.filename)


@router.post("/upload", response_model=PhotoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Photo file to upload"),
    description: Optional[str] = Form(None, max_length=500),
    season: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    campus: Optional[str] = Form(None),
    enable_ai: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    if season and season not in ["Spring", "Summer", "Autumn", "Winter"]:
        raise HTTPException(status_code=400, detail="Season must be one of: Spring, Summer, Autumn, Winter")
    if category and category not in ["Landscape", "Portrait", "Activity", "Documentary"]:
        raise HTTPException(status_code=400, detail="Category must be one of: Landscape, Portrait, Activity, Documentary")

    staged_original_path = None
    staged_thumb_path = None
    try:
        runtime_settings = await get_runtime_settings(db)
        photo_uuid, staged_original_path, original_filename, _ = await stage_photo_upload(file)
        processing_result = process_uploaded_image(
            staged_original_path,
            photo_uuid,
            output_dir=str(Path(staged_original_path).parent),
        )
        staged_thumb_path = processing_result.get("thumb_path")
        stored_media = get_storage().persist_photo_files(photo_uuid, staged_original_path, staged_thumb_path)

        processing_status = "pending" if enable_ai and runtime_settings.ai_enabled else "manual"
        photo = await photo_crud.create_photo(
            db,
            {
                "id": photo_uuid,
                "filename": original_filename,
                "original_path": stored_media.original_path,
                "thumb_path": stored_media.thumb_path,
                "width": processing_result.get("width"),
                "height": processing_result.get("height"),
                "file_size": stored_media.file_size,
                "mime_type": file.content_type,
                "exif_data": processing_result.get("exif_data", {}),
                "captured_at": processing_result.get("captured_at"),
                "description": description,
                "season": season,
                "category": category,
                "campus": campus,
                "status": "pending",
                "processing_status": processing_status,
            },
            str(current_user.id),
        )
        await ensure_default_taxonomy(db)

        if enable_ai and runtime_settings.ai_enabled:
            task = await create_ai_analysis_task(
                db,
                photo=photo,
                requested_by_id=current_user.id,
                provider=runtime_settings.ai_provider,
                model_id=runtime_settings.ai_model_id,
            )
            dispatch_ai_analysis_task(background_tasks, task.id)

        return PhotoUploadResponse(
            id=photo.id,
            filename=photo.filename,
            original_path=photo.original_path,
            thumb_path=photo.thumb_path,
            width=photo.width,
            height=photo.height,
            status=photo.status,
            message="Photo uploaded successfully",
        )
    except Exception as exc:  # noqa: BLE001
        cleanup_staged_files(staged_original_path, staged_thumb_path)
        raise HTTPException(status_code=500, detail=f"Failed to upload photo: {exc}") from exc
    finally:
        # Clean up temp files on success too (S3 backend copies, doesn't move)
        if staged_original_path:
            cleanup_staged_files(staged_original_path, staged_thumb_path)


@router.get("", response_model=PhotoListResponse)
async def list_photos(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    season: Optional[str] = None,
    category: Optional[str] = None,
    campus: Optional[str] = None,
    building: Optional[str] = None,
    gallery_series: Optional[str] = None,
    gallery_year: Optional[str] = None,
    photo_type: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    limit = min(limit, 100)
    photos, total = await photo_crud.get_photos(
        db,
        skip=skip,
        limit=limit,
        status=status,
        season=season,
        category=category,
        campus=campus,
        building=building,
        gallery_series=gallery_series,
        gallery_year=gallery_year,
        photo_type=photo_type,
        search=search,
        tag=tag,
    )
    return PhotoListResponse(
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
        items=await serialize_photos(db, photos),
    )


@router.get("/my-submissions", response_model=PhotoListResponse)
async def list_my_submissions(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    season: Optional[str] = None,
    category: Optional[str] = None,
    campus: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    limit = min(limit, 100)
    photos, total = await photo_crud.get_photos(
        db,
        skip=skip,
        limit=limit,
        status=status,
        season=season,
        category=category,
        campus=campus,
        search=search,
        uploader_id=current_user.id,
    )
    return PhotoListResponse(
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
        items=await serialize_photos(db, photos),
    )


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = await photo_crud.get_photo_with_tags(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    if not is_reviewer(current_user) and photo.uploader_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this photo")
    return await serialize_photo(db, photo)


@router.patch("/{photo_id}", response_model=PhotoResponse)
async def update_photo(
    photo_id: str,
    photo_update: PhotoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = await photo_crud.get_photo_with_tags(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.uploader_id != current_user.id and not is_reviewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to update this photo")
    updated_photo = await photo_crud.update_photo(db, photo, photo_update)
    return await serialize_photo(db, updated_photo)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = await photo_crud.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.uploader_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this photo")
    storage = get_storage()
    storage.delete_file(photo.original_path)
    storage.delete_file(photo.thumb_path)
    storage.delete_file(photo.processed_path)
    # Log BEFORE delete — photo_crud.delete_photo internally calls db.commit()
    # which also commits the flushed audit log
    await log_audit(db, user_id=current_user.id, action="photo.delete",
                    resource_type="photo", resource_id=photo_id,
                    detail=f"删除照片: {photo.filename}", request=request)
    await photo_crud.delete_photo(db, photo)
    return None


@router.post("/{photo_id}/approve", response_model=PhotoResponse)
async def approve_photo(
    photo_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    photo = await photo_crud.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.status = "approved"
    photo.published_at = datetime.utcnow()
    await log_audit(db, user_id=current_user.id, action="photo.approve",
                    resource_type="photo", resource_id=photo_id, request=request)
    # 通知上传者
    if photo.uploader_id and photo.uploader_id != current_user.id:
        await send_notification(db, user_id=photo.uploader_id, type="photo_approved",
                                title="您的照片已通过审核",
                                content=f"照片 {photo.filename} 已被审核通过并发布",
                                related_id=photo_id)
    await db.commit()
    await db.refresh(photo)
    return await serialize_photo(db, await photo_crud.get_photo_with_tags(db, photo_id))


@router.post("/{photo_id}/reject", response_model=PhotoResponse)
async def reject_photo(
    photo_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    photo = await photo_crud.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.status = "rejected"
    photo.published_at = None
    await log_audit(db, user_id=current_user.id, action="photo.reject",
                    resource_type="photo", resource_id=photo_id, request=request)
    # 通知上传者
    if photo.uploader_id and photo.uploader_id != current_user.id:
        await send_notification(db, user_id=photo.uploader_id, type="photo_rejected",
                                title="您的照片未通过审核",
                                content=f"照片 {photo.filename} 未通过审核",
                                related_id=photo_id)
    await db.commit()
    await db.refresh(photo)
    return await serialize_photo(db, await photo_crud.get_photo_with_tags(db, photo_id))


@router.post("/batch-approve")
async def batch_approve_photos(
    photo_ids: List[str],
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    updated_count = 0
    for photo_id in photo_ids:
        photo = await photo_crud.get_photo(db, photo_id)
        if photo:
            photo.status = "approved"
            photo.published_at = datetime.utcnow()
            updated_count += 1
    await log_audit(db, user_id=current_user.id, action="photo.batch_approve",
                    resource_type="photo", detail=f"批量通过 {updated_count} 张照片", request=request)
    await db.commit()
    return {"message": f"Successfully approved {updated_count} photos", "updated_count": updated_count, "total_requested": len(photo_ids)}


@router.post("/batch-reject")
async def batch_reject_photos(
    photo_ids: List[str],
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    updated_count = 0
    for photo_id in photo_ids:
        photo = await photo_crud.get_photo(db, photo_id)
        if photo:
            photo.status = "rejected"
            photo.published_at = None
            updated_count += 1
    await log_audit(db, user_id=current_user.id, action="photo.batch_reject",
                    resource_type="photo", detail=f"批量拒绝 {updated_count} 张照片", request=request)
    await db.commit()
    return {"message": f"Successfully rejected {updated_count} photos", "updated_count": updated_count, "total_requested": len(photo_ids)}


@router.post("/batch-delete")
async def batch_delete_photos(
    photo_ids: List[str],
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can delete photos in batch")
    storage = get_storage()
    deleted_count = 0
    for photo_id in photo_ids:
        photo = await photo_crud.get_photo(db, photo_id)
        if photo:
            storage.delete_file(photo.original_path)
            storage.delete_file(photo.thumb_path)
            storage.delete_file(photo.processed_path)
            await photo_crud.delete_photo(db, photo)
            deleted_count += 1
    await log_audit(db, user_id=current_user.id, action="photo.batch_delete",
                    resource_type="photo",
                    detail=f"批量删除 {deleted_count} 张照片",
                    request=request)
    await db.commit()
    return {"message": f"Successfully deleted {deleted_count} photos", "deleted_count": deleted_count, "total_requested": len(photo_ids)}


@router.post("/{photo_id}/tags", response_model=PhotoResponse)
async def add_photo_tags(
    photo_id: str,
    tag_names: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = await photo_crud.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.uploader_id != current_user.id and not is_reviewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to update tags for this photo")
    tag_ids = []
    for tag_name in tag_names:
        tag = await tag_crud.get_or_create_tag(db, tag_name)
        tag_ids.append(tag.id)
    await photo_crud.add_tags_to_photo(db, photo_id, tag_ids)
    return await serialize_photo(db, await photo_crud.get_photo_with_tags(db, photo_id))


@router.delete("/{photo_id}/tags/{tag_id}", response_model=PhotoResponse)
async def remove_photo_tag(
    photo_id: str,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = await photo_crud.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.uploader_id != current_user.id and not is_reviewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to update tags for this photo")

    from app.models.tag import PhotoTag

    await db.execute(
        PhotoTag.__table__.delete().where(
            PhotoTag.photo_id == photo_id,
            PhotoTag.tag_id == tag_id,
        )
    )
    await db.commit()
    tag = await tag_crud.get_tag(db, tag_id)
    if tag and tag.usage_count > 0:
        tag.usage_count -= 1
        await db.commit()
    return await serialize_photo(db, await photo_crud.get_photo_with_tags(db, photo_id))


@router.put("/{photo_id}/classifications", response_model=PhotoResponse)
async def update_photo_classifications(
    photo_id: str,
    body: "PhotoClassificationUpdateSchema",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch update photo classifications. Accepts { facet_key: node_id } mapping."""
    photo = await photo_crud.get_photo_with_tags(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.uploader_id != current_user.id and not is_reviewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to update this photo")

    from app.services.taxonomy import set_photo_classifications

    try:
        await set_photo_classifications(db, photo, body.classifications)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await db.commit()
    return await serialize_photo(db, await photo_crud.get_photo_with_tags(db, photo_id))


@router.delete("/{photo_id}/classifications/{facet_key}", response_model=PhotoResponse)
async def remove_photo_classification(
    photo_id: str,
    facet_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a single classification from a photo by facet key."""
    photo = await photo_crud.get_photo_with_tags(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.uploader_id != current_user.id and not is_reviewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to update this photo")

    from app.services.taxonomy import delete_photo_classification

    await delete_photo_classification(db, photo, facet_key)
    await db.commit()
    return await serialize_photo(db, await photo_crud.get_photo_with_tags(db, photo_id))


@router.post("/{photo_id}/classifications", response_model=PhotoResponse)
async def update_photo_classifications_post(
    photo_id: str,
    body: "PhotoClassificationUpdateSchema",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """POST alternative for updating photo classifications (workaround for proxy filtering)."""
    return await update_photo_classifications(photo_id, body, db, current_user)


@router.post("/{photo_id}/classifications/{facet_key}/remove", response_model=PhotoResponse)
async def remove_photo_classification_post(
    photo_id: str,
    facet_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """POST alternative for removing a photo classification (workaround for proxy filtering)."""
    return await remove_photo_classification(photo_id, facet_key, db, current_user)


@router.post("/{photo_id}/ai-analysis", response_model=AIAnalysisTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_photo_ai_analysis(
    photo_id: str,
    payload: AIAnalysisTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = await photo_crud.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.uploader_id != current_user.id and not is_reviewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to analyze this photo")

    existing = await get_latest_ai_task_for_photo(db, photo_id)
    if existing and existing.status in {"pending", "processing"} and not payload.force:
        return AIAnalysisTaskResponse.model_validate(existing)
    if existing and existing.status in {"completed", "applied"} and not payload.force:
        return AIAnalysisTaskResponse.model_validate(existing)

    runtime_settings = await get_runtime_settings(db)
    task = await create_ai_analysis_task(
        db,
        photo=photo,
        requested_by_id=current_user.id,
        provider=runtime_settings.ai_provider,
        model_id=runtime_settings.ai_model_id,
    )
    dispatch_ai_analysis_task(background_tasks, task.id)
    return AIAnalysisTaskResponse.model_validate(task)


class BatchAIAnalysisRequest(BaseModel):
    processing_status: str = Field(default="pending", description="Filter by processing_status")
    category: Optional[str] = Field(default=None, description="Filter by category")
    created_after: Optional[datetime] = Field(default=None, description="Filter photos created after this timestamp")
    max_count: int = Field(default=50, ge=1, le=100, description="Max number of AI tasks to create")
    prompt_version: str = Field(default="v3", description="Prompt version to use (v2, v3)")


class BatchAIAnalysisResponse(BaseModel):
    tasks_created: int
    photos_scanned: int
    photos_matched: int
    photos_skipped_no_path: int
    photos_skipped_has_task: int
    filters_applied: dict


@router.post("/batch-ai-analysis", response_model=BatchAIAnalysisResponse)
async def batch_ai_analysis(
    payload: BatchAIAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Admin-only: trigger AI analysis for multiple photos in batch."""
    conditions = [Photo.original_path.isnot(None), Photo.original_path != ""]
    if payload.processing_status:
        conditions.append(Photo.processing_status == payload.processing_status)
    if payload.category:
        conditions.append(Photo.category == payload.category)
    if payload.created_after:
        conditions.append(Photo.created_at >= payload.created_after)

    result = await db.execute(
        select(Photo).where(and_(*conditions)).limit(payload.max_count * 3)
    )
    photos = result.scalars().all()

    photos_scanned = len(photos)
    photos_skipped_no_path = 0
    photos_skipped_has_task = 0
    tasks_created = 0

    runtime_settings = await get_runtime_settings(db)

    for photo in photos:
        if not photo.original_path:
            photos_skipped_no_path += 1
            continue

        existing = await get_latest_ai_task_for_photo(db, photo.id)
        if existing and existing.status in {"pending", "processing", "completed", "applied"}:
            photos_skipped_has_task += 1
            continue

        task = await create_ai_analysis_task(
            db,
            photo=photo,
            requested_by_id=current_user.id,
            provider=runtime_settings.ai_provider,
            model_id=runtime_settings.ai_model_id,
        )
        dispatch_ai_analysis_task(background_tasks, task.id)
        tasks_created += 1

        if tasks_created >= payload.max_count:
            break

    return BatchAIAnalysisResponse(
        tasks_created=tasks_created,
        photos_scanned=photos_scanned,
        photos_matched=tasks_created,
        photos_skipped_no_path=photos_skipped_no_path,
        photos_skipped_has_task=photos_skipped_has_task,
        filters_applied={
            "processing_status": payload.processing_status,
            "category": payload.category,
            "created_after": payload.created_after.isoformat() if payload.created_after else None,
        },
    )


@router.get("/{photo_id}/ai-analysis", response_model=Optional[AIAnalysisTaskResponse])
async def get_photo_ai_analysis(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = await photo_crud.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    if photo.uploader_id != current_user.id and not is_reviewer(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to access this photo")
    task = await get_latest_ai_task_for_photo(db, photo_id)
    return AIAnalysisTaskResponse.model_validate(task) if task else None


@router.post("/{photo_id}/ai-analysis/{task_id}/apply", response_model=AIApplyResponse)
async def apply_photo_ai_analysis(
    photo_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    task = await get_ai_task(db, task_id)
    if task is None or task.photo_id != photo_id:
        raise HTTPException(status_code=404, detail="AI task not found")
    unresolved = await apply_ai_analysis_task(db, task, current_user.id)
    return AIApplyResponse(applied=True, task=AIAnalysisTaskResponse.model_validate(task), unresolved_classifications=unresolved)


@router.post("/{photo_id}/ai-analysis/{task_id}/ignore", response_model=AIAnalysisTaskResponse)
async def ignore_photo_ai_analysis(
    photo_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    task = await get_ai_task(db, task_id)
    if task is None or task.photo_id != photo_id:
        raise HTTPException(status_code=404, detail="AI task not found")
    task.status = "ignored"
    task.reviewed_by_id = current_user.id
    task.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)
    return AIAnalysisTaskResponse.model_validate(task)
