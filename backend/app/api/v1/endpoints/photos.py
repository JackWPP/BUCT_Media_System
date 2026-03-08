"""
Photo API endpoints

照片相关 API 端点，包括公开访问、上传、审核等功能。
支持基于系统配置的人像照片可见性控制。
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.deps import (
    get_db,
    get_current_user,
    get_current_auditor_user,
    get_optional_current_user,
    get_optional_current_user_for_media,
    get_portrait_visibility,
)
from app.models.user import User
from app.models.photo import Photo
from app.models.system_config import PortraitVisibility
from app.schemas.photo import (
    PhotoResponse, PhotoListResponse, PhotoUploadResponse,
    PhotoUpdate
)
from app.crud import photo as photo_crud
from app.crud import tag as tag_crud
from app.crud import permission as permission_crud
from app.services.storage import save_photo_file, delete_file
from app.services.image_processing import process_uploaded_image
from app.services.ai_tagging import analyze_photo_with_ai
import os

logger = logging.getLogger(__name__)


router = APIRouter()


def is_reviewer(user: Optional[User]) -> bool:
    """Return whether the user can review global photo content."""
    return bool(user and user.role in ("admin", "auditor"))


async def can_access_portrait_photo(
    db: AsyncSession,
    current_user: Optional[User],
    portrait_visibility: str
) -> bool:
    """Check whether the current user may access portrait content."""
    if portrait_visibility == PortraitVisibility.PUBLIC:
        return True

    if not current_user:
        return False

    if portrait_visibility == PortraitVisibility.LOGIN_REQUIRED:
        return True

    return await permission_crud.check_permission(
        db, current_user.id, "category", "Portrait", "view"
    )


async def can_access_photo_publicly(
    db: AsyncSession,
    photo: Photo,
    current_user: Optional[User],
    portrait_visibility: str
) -> bool:
    """Check whether a photo is visible through the public access path."""
    if photo.status != "approved":
        return False

    if photo.category != "Portrait":
        return True

    return await can_access_portrait_photo(db, current_user, portrait_visibility)


async def serialize_photo(db: AsyncSession, photo: Photo) -> PhotoResponse:
    """Convert ORM photo model to API response."""
    tags = await photo_crud.get_photo_tags(db, photo.id)
    tag_names = [tag.name for tag in tags]

    photo_dict = {**photo.__dict__}
    photo_dict.pop("_sa_instance_state", None)
    photo_dict["tags"] = tag_names
    photo_dict["uploader_name"] = None

    return PhotoResponse(**photo_dict)


async def serialize_photos(db: AsyncSession, photos: List[Photo]) -> List[PhotoResponse]:
    """Convert a list of ORM photo models to API responses."""
    return [await serialize_photo(db, photo) for photo in photos]


def find_original_photo_path(photo: Photo) -> Optional[str]:
    """Find the stored original file path for a photo."""
    from app.core.config import get_settings

    settings = get_settings()

    ext = ""
    if photo.filename:
        _, ext = os.path.splitext(photo.filename)
    if not ext and photo.original_path:
        _, ext = os.path.splitext(photo.original_path)

    candidates = []
    if ext:
        candidates.append(f"{photo.id}{ext}")
        if ext.lower() != ".jpg":
            candidates.append(f"{photo.id}.jpg")

    if photo.original_path:
        clean_path = photo.original_path.replace("\\", "/")
        basename = os.path.basename(clean_path)
        if basename not in candidates:
            candidates.append(basename)

    if photo.filename and photo.filename not in candidates:
        candidates.append(photo.filename)

    for filename in candidates:
        file_path = os.path.join(settings.UPLOAD_DIR, "originals", filename)
        if os.path.exists(file_path):
            return file_path

    if photo.original_path and os.path.exists(photo.original_path):
        return photo.original_path

    logger.error(
        "Image not found for photo %s. Tried: %s in %s/originals",
        photo.id,
        candidates,
        settings.UPLOAD_DIR,
    )
    return None


def find_thumbnail_path(photo: Photo) -> Optional[str]:
    """Find the stored thumbnail path for a photo."""
    from app.core.config import get_settings

    settings = get_settings()
    filename = f"{photo.id}_thumb.jpg"
    file_path = os.path.join(settings.UPLOAD_DIR, "thumbnails", filename)

    if os.path.exists(file_path):
        return file_path

    if photo.thumb_path and os.path.exists(photo.thumb_path):
        return photo.thumb_path

    logger.error("Thumbnail not found for photo %s", photo.id)
    return None


@router.get("/public", response_model=PhotoListResponse)
async def list_public_photos(
    skip: int = 0,
    limit: int = 20,
    season: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    portrait_visibility: str = Depends(get_portrait_visibility)
):
    """
    List approved photos for public access
    
    根据系统配置的人像可见性设置，对 Portrait 类别照片进行过滤：
    - public: 所有人可见
    - login_required: 仅登录用户可见
    - authorized_only: 仅授权用户可见（暂同 login_required）
    
    如果用户未登录且请求 Portrait 类别，该类别将被自动排除。
    
    排序参数：
    - sort_by: created_at (默认), views, published_at
    - sort_order: desc (默认), asc
    """
    # Limit maximum page size
    limit = min(limit, 100)
    
    # Validate sort_by
    if sort_by not in ["created_at", "views", "published_at"]:
        sort_by = "created_at"
    if sort_order not in ["asc", "desc"]:
        sort_order = "desc"
    
    # 检查是否需要过滤人像照片
    should_filter_portrait = False
    if portrait_visibility == PortraitVisibility.LOGIN_REQUIRED:
        # 需要登录才能查看人像
        if not current_user:
            should_filter_portrait = True
    elif portrait_visibility == PortraitVisibility.AUTHORIZED_ONLY:
        # 仅授权用户可见 - 检查 ResourcePermission
        if not current_user:
            should_filter_portrait = True
        else:
            # 检查用户是否有 Portrait 类别的查看权限
            if not await can_access_portrait_photo(db, current_user, portrait_visibility):
                should_filter_portrait = True
    # portrait_visibility == 'public' 时不过滤

    # 构建排除类别列表
    exclude_categories = []
    if should_filter_portrait:
        exclude_categories.append('Portrait')
    
    photos, total = await photo_crud.get_photos(
        db,
        skip=skip,
        limit=limit,
        status='approved',  # Only approved photos
        season=season,
        category=category,
        search=search,
        tag=tag,
        exclude_categories=exclude_categories if exclude_categories else None,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    photo_responses = await serialize_photos(db, photos)
    
    page = skip // limit + 1 if limit > 0 else 1
    
    return PhotoListResponse(
        total=total,
        page=page,
        page_size=limit,
        items=photo_responses
    )


@router.get("/{photo_id}/image/original")
async def get_photo_image(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user_for_media),
    portrait_visibility: str = Depends(get_portrait_visibility),
):
    """
    获取原始照片文件
    
    通过照片ID查找并返回原始图片文件。
    使用 UPLOAD_DIR 配置构建路径，忽略数据库中的绝对路径。
    """
    photo = await photo_crud.get_photo(db, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    can_access = (
        is_reviewer(current_user)
        or (current_user and photo.uploader_id == current_user.id)
        or await can_access_photo_publicly(db, photo, current_user, portrait_visibility)
    )
    if not can_access:
        raise HTTPException(status_code=404, detail="Photo not found")

    file_path = find_original_photo_path(photo)
    if not file_path:
        raise HTTPException(status_code=404, detail="Image file not found on server")

    return FileResponse(file_path)


@router.get("/{photo_id}/image/thumbnail")
async def get_photo_thumbnail(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user_for_media),
    portrait_visibility: str = Depends(get_portrait_visibility),
):
    """
    获取照片缩略图
    
    缩略图文件名格式为 {photo_id}_thumb.jpg
    """
    photo = await photo_crud.get_photo(db, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    can_access = (
        is_reviewer(current_user)
        or (current_user and photo.uploader_id == current_user.id)
        or await can_access_photo_publicly(db, photo, current_user, portrait_visibility)
    )
    if not can_access:
        raise HTTPException(status_code=404, detail="Photo not found")

    file_path = find_thumbnail_path(photo)
    if not file_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(file_path)


@router.get("/public/{photo_id}", response_model=PhotoResponse)
async def get_public_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    portrait_visibility: str = Depends(get_portrait_visibility)
):
    """
    Get a specific approved photo by ID
    
    根据系统配置的人像可见性设置，对 Portrait 类别照片进行权限检查。
    """
    photo = await photo_crud.get_photo_with_tags(db, photo_id)
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    if not await can_access_photo_publicly(db, photo, current_user, portrait_visibility):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    return await serialize_photo(db, photo)


async def process_photo_ai_tagging(photo_id: str, original_path: str):
    """
    后台任务: 使用 AI 分析照片并更新标签
    
    Args:
        photo_id: 照片 ID
        original_path: 原始图片路径
    """
    from app.core.database import AsyncSessionLocal
    
    logger.info(f"开始 AI 分析照片: {photo_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            # 更新状态为处理中
            photo = await photo_crud.get_photo(db, photo_id)
            if not photo:
                logger.error(f"照片不存在: {photo_id}")
                return
            
            photo.processing_status = 'processing'
            await db.commit()
            
            # 调用 AI 分析
            ai_result = await analyze_photo_with_ai(original_path)
            
            if not ai_result:
                # AI 分析失败
                photo.processing_status = 'failed'
                await db.commit()
                logger.error(f"AI 分析失败: {photo_id}")
                return
            
            # 更新 season 和 category (如果未手动设置)
            if not photo.season and 'season' in ai_result:
                photo.season = ai_result['season']
            if not photo.category and 'category' in ai_result:
                photo.category = ai_result['category']
            
            # 处理 objects 标签
            if 'objects' in ai_result and ai_result['objects']:
                tag_ids = []
                for tag_name in ai_result['objects']:
                    # 获取或创建标签
                    tag = await tag_crud.get_or_create_tag(db, tag_name.lower())
                    tag_ids.append(tag.id)
                
                # 添加标签到照片
                if tag_ids:
                    await photo_crud.add_tags_to_photo(db, photo_id, tag_ids)
            
            # 更新状态为完成
            photo.processing_status = 'completed'
            await db.commit()
            
            logger.info(f"AI 分析完成: {photo_id}, season={photo.season}, category={photo.category}, tags={len(ai_result.get('objects', []))}")
            
        except Exception as e:
            logger.error(f"AI 分析过程出错: {photo_id}, error={str(e)}")
            # 更新状态为失败
            try:
                photo = await photo_crud.get_photo(db, photo_id)
                if photo:
                    photo.processing_status = 'failed'
                    await db.commit()
            except:
                pass


@router.post("/upload", response_model=PhotoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Photo file to upload"),
    description: Optional[str] = Form(None, max_length=500),
    season: Optional[str] = Form(None, description="Spring/Summer/Autumn/Winter"),
    category: Optional[str] = Form(None, description="Landscape/Portrait/Activity/Documentary"),
    enable_ai: bool = Form(True, description="Enable AI auto-tagging"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a new photo
    
    - **file**: Photo file (JPEG, PNG, etc.)
    - **description**: Optional description
    - **season**: Optional season classification
    - **category**: Optional category classification
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Validate season
    if season and season not in ['Spring', 'Summer', 'Autumn', 'Winter']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Season must be one of: Spring, Summer, Autumn, Winter"
        )
    
    # Validate category
    if category and category not in ['Landscape', 'Portrait', 'Activity', 'Documentary']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category must be one of: Landscape, Portrait, Activity, Documentary"
        )
    
    try:
        # Save uploaded file
        photo_uuid, original_path, original_filename, file_extension = await save_photo_file(file)
        
        # Process image (create thumbnail, extract EXIF, etc.)
        processing_result = process_uploaded_image(original_path, photo_uuid)
        
        # Get file size
        file_size = os.path.getsize(original_path) if os.path.exists(original_path) else None
        
        # Determine processing status based on AI enablement
        processing_status = 'pending' if enable_ai and not season and not category else 'completed'
        
        # Create photo record in database
        photo_data = {
            'id': photo_uuid,  # Already a string from save_photo_file
            'filename': original_filename,
            'original_path': original_path,
            'thumb_path': processing_result.get('thumb_path'),
            'width': processing_result.get('width'),
            'height': processing_result.get('height'),
            'file_size': file_size,
            'mime_type': file.content_type,
            'exif_data': processing_result.get('exif_data', {}),
            'captured_at': processing_result.get('captured_at'),
            'description': description,
            'season': season,
            'category': category,
            'status': 'pending',  # Default to pending, will be approved manually
            'processing_status': processing_status
        }
        
        photo = await photo_crud.create_photo(db, photo_data, str(current_user.id))
        
        # Add AI tagging background task if enabled and season/category not provided
        if enable_ai and (not season or not category):
            background_tasks.add_task(
                process_photo_ai_tagging,
                photo_id=photo.id,
                original_path=original_path
            )
        
        return PhotoUploadResponse(
            id=photo.id,
            filename=photo.filename,
            original_path=photo.original_path,
            thumb_path=photo.thumb_path,
            width=photo.width,
            height=photo.height,
            status=photo.status,
            message="Photo uploaded successfully"
        )
    
    except Exception as e:
        # Clean up uploaded file if database operation fails
        if 'original_path' in locals() and os.path.exists(original_path):
            delete_file(original_path)
        if 'thumb_path' in processing_result and processing_result['thumb_path']:
            delete_file(processing_result['thumb_path'])
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload photo: {str(e)}"
        )


@router.get("", response_model=PhotoListResponse)
async def list_photos(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    season: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user)
):
    """
    List photos with filtering and pagination
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (max 100)
    - **status**: Filter by status
    - **season**: Filter by season
    - **category**: Filter by category
    - **search**: Search in filename, description, and tags
    - **tag**: Filter by specific tag name
    """
    # Limit maximum page size
    limit = min(limit, 100)
    
    photos, total = await photo_crud.get_photos(
        db,
        skip=skip,
        limit=limit,
        status=status,
        season=season,
        category=category,
        search=search,
        tag=tag
    )
    
    photo_responses = await serialize_photos(db, photos)
    
    page = skip // limit + 1 if limit > 0 else 1
    
    return PhotoListResponse(
        total=total,
        page=page,
        page_size=limit,
        items=photo_responses
    )


@router.get("/my-submissions", response_model=PhotoListResponse)
async def list_my_submissions(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    season: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List current user's submissions (all statuses)
    """
    # Limit maximum page size
    limit = min(limit, 100)
    
    # Force filter by current user
    photos, total = await photo_crud.get_photos(
        db,
        skip=skip,
        limit=limit,
        status=status,
        season=season,
        category=category,
        uploader_id=current_user.id
    )
    
    photo_responses = await serialize_photos(db, photos)
    
    page = skip // limit + 1 if limit > 0 else 1
    
    return PhotoListResponse(
        total=total,
        page=page,
        page_size=limit,
        items=photo_responses
    )


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific photo by ID
    """
    photo = await photo_crud.get_photo_with_tags(db, photo_id)
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    if not is_reviewer(current_user) and photo.uploader_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this photo"
        )

    return await serialize_photo(db, photo)


@router.patch("/{photo_id}", response_model=PhotoResponse)
async def update_photo(
    photo_id: str,
    photo_update: PhotoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a photo's metadata
    
    Users can only update their own photos unless they are admin
    """
    photo = await photo_crud.get_photo(db, photo_id)
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Check permission
    if photo.uploader_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this photo"
        )
    
    # Validate season and category if provided
    if photo_update.season and photo_update.season not in ['Spring', 'Summer', 'Autumn', 'Winter']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Season must be one of: Spring, Summer, Autumn, Winter"
        )
    
    if photo_update.category and photo_update.category not in ['Landscape', 'Portrait', 'Activity', 'Documentary']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category must be one of: Landscape, Portrait, Activity, Documentary"
        )
    
    updated_photo = await photo_crud.update_photo(db, photo, photo_update)
    
    return await serialize_photo(db, updated_photo)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a photo
    
    Users can only delete their own photos unless they are admin
    """
    photo = await photo_crud.get_photo(db, photo_id)
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Check permission
    if photo.uploader_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this photo"
        )
    
    # Delete physical files
    if photo.original_path and os.path.exists(photo.original_path):
        delete_file(photo.original_path)
    
    if photo.thumb_path and os.path.exists(photo.thumb_path):
        delete_file(photo.thumb_path)
    
    if photo.processed_path and os.path.exists(photo.processed_path):
        delete_file(photo.processed_path)
    
    # Delete database record
    await photo_crud.delete_photo(db, photo)
    
    return None


@router.post("/{photo_id}/approve", response_model=PhotoResponse)
async def approve_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user)
):
    """
    Approve a photo (publish it)
    
    Only reviewers can approve photos
    """
    photo = await photo_crud.get_photo(db, photo_id)
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Update status to approved
    from datetime import datetime
    photo.status = 'approved'
    photo.published_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(photo)
    
    return await serialize_photo(db, photo)


@router.post("/{photo_id}/reject", response_model=PhotoResponse)
async def reject_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user)
):
    """
    Reject a photo (unpublish it)
    
    Only reviewers can reject photos
    """
    photo = await photo_crud.get_photo(db, photo_id)
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Update status to rejected
    photo.status = 'rejected'
    photo.published_at = None
    
    await db.commit()
    await db.refresh(photo)
    
    return await serialize_photo(db, photo)


@router.post("/batch-approve")
async def batch_approve_photos(
    photo_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user)
):
    """
    Batch approve multiple photos
    
    Only reviewers can approve photos
    """
    from datetime import datetime
    updated_count = 0
    
    for photo_id in photo_ids:
        photo = await photo_crud.get_photo(db, photo_id)
        if photo:
            photo.status = 'approved'
            photo.published_at = datetime.utcnow()
            updated_count += 1
    
    await db.commit()
    
    return {
        "message": f"Successfully approved {updated_count} photos",
        "updated_count": updated_count,
        "total_requested": len(photo_ids)
    }


@router.post("/batch-reject")
async def batch_reject_photos(
    photo_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user)
):
    """
    Batch reject multiple photos
    
    Only reviewers can reject photos
    """
    updated_count = 0
    
    for photo_id in photo_ids:
        photo = await photo_crud.get_photo(db, photo_id)
        if photo:
            photo.status = 'rejected'
            photo.published_at = None
            updated_count += 1
    
    await db.commit()
    
    return {
        "message": f"Successfully rejected {updated_count} photos",
        "updated_count": updated_count,
        "total_requested": len(photo_ids)
    }


@router.post("/batch-delete")
async def batch_delete_photos(
    photo_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Batch delete multiple photos
    
    Only admins can delete photos in batch
    """
    # Check admin permission
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete photos in batch"
        )
    
    deleted_count = 0
    
    for photo_id in photo_ids:
        photo = await photo_crud.get_photo(db, photo_id)
        if photo:
            # Delete physical files
            if photo.original_path and os.path.exists(photo.original_path):
                delete_file(photo.original_path)
            
            if photo.thumb_path and os.path.exists(photo.thumb_path):
                delete_file(photo.thumb_path)
            
            if photo.processed_path and os.path.exists(photo.processed_path):
                delete_file(photo.processed_path)
            
            # Delete database record
            await photo_crud.delete_photo(db, photo)
            deleted_count += 1
    
    return {
        "message": f"Successfully deleted {deleted_count} photos",
        "deleted_count": deleted_count,
        "total_requested": len(photo_ids)
    }


@router.post("/{photo_id}/tags", response_model=PhotoResponse)
async def add_photo_tags(
    photo_id: str,
    tag_names: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add tags to a photo by tag names
    
    Tags will be created automatically if they don't exist
    Users can only update tags for their own photos unless they are admin
    """
    photo = await photo_crud.get_photo(db, photo_id)
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Check permission
    if photo.uploader_id != current_user.id and not is_reviewer(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update tags for this photo"
        )
    
    # Get or create tags
    tag_ids = []
    for tag_name in tag_names:
        tag = await tag_crud.get_or_create_tag(db, tag_name)
        tag_ids.append(tag.id)
    
    # Add tags to photo
    await photo_crud.add_tags_to_photo(db, photo_id, tag_ids)
    
    updated_photo = await photo_crud.get_photo(db, photo_id)
    return await serialize_photo(db, updated_photo)


@router.delete("/{photo_id}/tags/{tag_id}", response_model=PhotoResponse)
async def remove_photo_tag(
    photo_id: str,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a tag from a photo
    
    Users can only update tags for their own photos unless they are admin
    """
    photo = await photo_crud.get_photo(db, photo_id)
    
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Check permission
    if photo.uploader_id != current_user.id and not is_reviewer(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update tags for this photo"
        )
    
    # Remove tag from photo
    from app.models.tag import PhotoTag
    await db.execute(
        PhotoTag.__table__.delete().where(
            PhotoTag.photo_id == photo_id,
            PhotoTag.tag_id == tag_id
        )
    )
    await db.commit()
    
    # Update tag usage count
    tag = await tag_crud.get_tag(db, tag_id)
    if tag and tag.usage_count > 0:
        tag.usage_count -= 1
        await db.commit()
    
    updated_photo = await photo_crud.get_photo(db, photo_id)
    return await serialize_photo(db, updated_photo)


@router.get("/{photo_id}/download")
async def download_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user_for_media),
    portrait_visibility: str = Depends(get_portrait_visibility),
):
    """
    Download photo by ID. Handles both relative and absolute paths.
    """
    photo = await photo_crud.get_photo(db, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    can_access = (
        is_reviewer(current_user)
        or (current_user and photo.uploader_id == current_user.id)
        or await can_access_photo_publicly(db, photo, current_user, portrait_visibility)
    )
    if not can_access:
        raise HTTPException(status_code=404, detail="Photo not found")

    file_path = find_original_photo_path(photo)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=file_path,
        filename=photo.filename,
        media_type="application/octet-stream"
    )
