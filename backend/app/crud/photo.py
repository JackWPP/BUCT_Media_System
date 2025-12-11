"""
CRUD operations for Photo
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.photo import Photo
from app.models.tag import PhotoTag, Tag
from app.schemas.photo import PhotoCreate, PhotoUpdate


async def create_photo(
    db: AsyncSession,
    photo_data: dict,
    uploader_id: str
) -> Photo:
    """
    Create a new photo record
    
    Args:
        db: Database session
        photo_data: Photo data dictionary
        uploader_id: ID of the user uploading the photo
    
    Returns:
        Created Photo object
    """
    photo = Photo(
        uploader_id=uploader_id,
        **photo_data
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo


async def get_photo(db: AsyncSession, photo_id: str) -> Optional[Photo]:
    """
    Get a photo by ID
    
    Args:
        db: Database session
        photo_id: Photo ID
    
    Returns:
        Photo object or None
    """
    result = await db.execute(
        select(Photo).where(Photo.id == photo_id)
    )
    return result.scalar_one_or_none()


async def get_photo_with_tags(db: AsyncSession, photo_id: str) -> Optional[Photo]:
    """
    Get a photo by ID with its tags loaded
    
    Args:
        db: Database session
        photo_id: Photo ID
    
    Returns:
        Photo object with tags or None
    """
    result = await db.execute(
        select(Photo)
        .options(selectinload(Photo.tags))
        .where(Photo.id == photo_id)
    )
    return result.scalar_one_or_none()


async def get_photos(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    uploader_id: Optional[str] = None,
    status: Optional[str] = None,
    season: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None
) -> tuple[List[Photo], int]:
    """
    Get photos with filtering and pagination
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        uploader_id: Filter by uploader
        status: Filter by status
        season: Filter by season
        category: Filter by category
        search: Search in filename and description
    
    Returns:
        Tuple of (list of photos, total count)
    """
    query = select(Photo)
    count_query = select(func.count(Photo.id))
    
    # Apply filters
    if uploader_id:
        query = query.where(Photo.uploader_id == uploader_id)
        count_query = count_query.where(Photo.uploader_id == uploader_id)
    
    if status:
        query = query.where(Photo.status == status)
        count_query = count_query.where(Photo.status == status)
    
    if season:
        query = query.where(Photo.season == season)
        count_query = count_query.where(Photo.season == season)
    
    if category:
        query = query.where(Photo.category == category)
        count_query = count_query.where(Photo.category == category)
    
    if search:
        search_pattern = f"%{search}%"
        search_filter = or_(
            Photo.filename.ilike(search_pattern),
            Photo.description.ilike(search_pattern)
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Apply pagination and ordering
    query = query.order_by(Photo.created_at.desc()).offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    photos = result.scalars().all()
    
    return list(photos), total


async def update_photo(
    db: AsyncSession,
    photo: Photo,
    photo_update: PhotoUpdate
) -> Photo:
    """
    Update a photo
    
    Args:
        db: Database session
        photo: Photo object to update
        photo_update: Update data
    
    Returns:
        Updated Photo object
    """
    update_data = photo_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(photo, field, value)
    
    await db.commit()
    await db.refresh(photo)
    return photo


async def update_photo_processing_status(
    db: AsyncSession,
    photo: Photo,
    processing_status: str,
    processed_path: Optional[str] = None
) -> Photo:
    """
    Update photo processing status
    
    Args:
        db: Database session
        photo: Photo object
        processing_status: New processing status
        processed_path: Path to processed image (optional)
    
    Returns:
        Updated Photo object
    """
    photo.processing_status = processing_status
    if processed_path:
        photo.processed_path = processed_path
    
    await db.commit()
    await db.refresh(photo)
    return photo


async def delete_photo(db: AsyncSession, photo: Photo) -> None:
    """
    Delete a photo
    
    Args:
        db: Database session
        photo: Photo object to delete
    """
    await db.delete(photo)
    await db.commit()


async def add_tags_to_photo(
    db: AsyncSession,
    photo_id: str,
    tag_ids: List[int]
) -> None:
    """
    Add tags to a photo
    
    Args:
        db: Database session
        photo_id: Photo ID
        tag_ids: List of tag IDs to add
    """
    # Remove existing tags
    await db.execute(
        PhotoTag.__table__.delete().where(PhotoTag.photo_id == photo_id)
    )
    
    # Add new tags
    for tag_id in tag_ids:
        photo_tag = PhotoTag(photo_id=photo_id, tag_id=tag_id)
        db.add(photo_tag)
    
    await db.commit()


async def get_photo_tags(db: AsyncSession, photo_id: str) -> List[Tag]:
    """
    Get all tags for a photo
    
    Args:
        db: Database session
        photo_id: Photo ID
    
    Returns:
        List of Tag objects
    """
    result = await db.execute(
        select(Tag)
        .join(PhotoTag)
        .where(PhotoTag.photo_id == photo_id)
    )
    return list(result.scalars().all())
