"""
Tag API endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user, get_current_auditor_user
from app.models.user import User
from app.schemas.tag import TagCreate, TagUpdate, TagResponse, TagListResponse, TagSuggestion
from app.crud import tag as tag_crud


router = APIRouter()


@router.get("/public", response_model=TagListResponse)
async def list_public_tags(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List tags with filtering and pagination (no authentication required)
    """
    limit = min(limit, 200)
    
    tags, total = await tag_crud.get_tags(
        db,
        skip=skip,
        limit=limit,
        search=search,
        category=category
    )
    
    tag_responses = [TagResponse.model_validate(tag) for tag in tags]
    
    return TagListResponse(
        total=total,
        items=tag_responses
    )


@router.get("", response_model=TagListResponse)
async def list_tags(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List tags with filtering and pagination
    
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return (max 200)
    - **search**: Search in tag name
    - **category**: Filter by category
    """
    # Limit maximum page size
    limit = min(limit, 200)
    
    tags, total = await tag_crud.get_tags(
        db,
        skip=skip,
        limit=limit,
        search=search,
        category=category
    )
    
    tag_responses = [TagResponse.model_validate(tag) for tag in tags]
    
    return TagListResponse(
        total=total,
        items=tag_responses
    )


@router.get("/popular", response_model=list[TagResponse])
async def get_popular_tags(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get popular tags sorted by usage count (no authentication required)
    
    - **limit**: Maximum number of tags to return (max 50)
    """
    limit = min(limit, 50)
    
    tags = await tag_crud.get_popular_tags(db, limit=limit)
    
    return [TagResponse.model_validate(tag) for tag in tags]


@router.get("/suggestions", response_model=list[TagSuggestion])
async def get_tag_suggestions(
    q: str,
    limit: int = 12,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest existing canonical tags and aliases for tag entry."""
    limit = min(limit, 30)
    return await tag_crud.get_tag_suggestions(db, q, limit=limit)


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user)
):
    """
    Create a new tag
    
    Only reviewers can create tags manually
    """
    # Check if tag already exists
    existing_tag = await tag_crud.get_tag_by_name(db, tag.name)
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag '{tag.name}' already exists"
        )
    
    created_tag = await tag_crud.create_tag(db, tag)
    
    return TagResponse.model_validate(created_tag)


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific tag by ID
    """
    tag = await tag_crud.get_tag(db, tag_id)
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return TagResponse.model_validate(tag)


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    tag_update: TagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user)
):
    """
    Update a tag
    
    Only reviewers can update tags
    """
    tag = await tag_crud.get_tag(db, tag_id)
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # If name is being updated, check for duplicates
    if tag_update.name and tag_update.name.lower() != tag.name:
        existing_tag = await tag_crud.get_tag_by_name(db, tag_update.name)
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tag '{tag_update.name}' already exists"
            )
    
    updated_tag = await tag_crud.update_tag(db, tag, tag_update)
    
    return TagResponse.model_validate(updated_tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user)
):
    """
    Delete a tag
    
    Only reviewers can delete tags
    Note: This will also remove all photo-tag associations
    """
    tag = await tag_crud.get_tag(db, tag_id)
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    await tag_crud.delete_tag(db, tag)

    return None


# ---------------------------------------------------------------------------
# Tag quality and management endpoints (Phase 2A)
# ---------------------------------------------------------------------------

from sqlalchemy import func, select as sa_select
from app.models.tag import Tag, PhotoTag
from app.models.photo import Photo
from app.models.ai_analysis import AIAnalysisTask


@router.get("/quality/stats")
async def get_tag_quality_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    """Get overall tag quality statistics."""
    # Total tags
    total_result = await db.execute(sa_select(func.count(Tag.id)))
    total_tags = total_result.scalar_one()

    # Tags with 0 usage
    unused_result = await db.execute(
        sa_select(func.count(Tag.id)).where(Tag.usage_count == 0)
    )
    unused_tags = unused_result.scalar_one()

    # Tags with category
    categorized_result = await db.execute(
        sa_select(func.count(Tag.id)).where(Tag.category.isnot(None))
    )
    categorized_tags = categorized_result.scalar_one()

    # Category distribution
    cat_dist_result = await db.execute(
        sa_select(Tag.category, func.count(Tag.id))
        .group_by(Tag.category)
        .order_by(func.count(Tag.id).desc())
    )
    category_distribution = {row[0] or "uncategorized": row[1] for row in cat_dist_result.all()}

    # Top 20 most used tags
    top_tags_result = await db.execute(
        sa_select(Tag.name, Tag.usage_count, Tag.category)
        .order_by(Tag.usage_count.desc())
        .limit(20)
    )
    top_tags = [
        {"name": row[0], "usage_count": row[1], "category": row[2]}
        for row in top_tags_result.all()
    ]

    # Tags used only once (potential noise)
    single_use_result = await db.execute(
        sa_select(func.count(Tag.id)).where(Tag.usage_count == 1)
    )
    single_use_tags = single_use_result.scalar_one()

    # Total photos with tags
    photos_with_tags_result = await db.execute(
        sa_select(func.count(func.distinct(PhotoTag.photo_id)))
    )
    photos_with_tags = photos_with_tags_result.scalar_one()

    # Total photos
    total_photos_result = await db.execute(sa_select(func.count(Photo.id)))
    total_photos = total_photos_result.scalar_one()

    return {
        "total_tags": total_tags,
        "unused_tags": unused_tags,
        "categorized_tags": categorized_tags,
        "uncategorized_tags": total_tags - categorized_tags,
        "single_use_tags": single_use_tags,
        "category_distribution": category_distribution,
        "top_tags": top_tags,
        "photos_with_tags": photos_with_tags,
        "total_photos": total_photos,
        "tag_coverage_rate": round(photos_with_tags / max(total_photos, 1) * 100, 1),
    }


class TagMergeRequest(BaseModel):
    source_tag_ids: list[int] = Field(..., min_length=1, description="Tag IDs to merge from")
    target_tag_id: int = Field(..., description="Tag ID to merge into (keep this one)")


@router.post("/merge")
async def merge_tags(
    payload: TagMergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    """Merge multiple tags into one target tag.

    All photos associated with source tags will be re-associated with the target tag.
    Source tags will be deleted after merge.
    """
    # Verify target exists
    target = await tag_crud.get_tag(db, payload.target_tag_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target tag not found")

    # Verify all source tags exist
    source_tags = []
    for sid in payload.source_tag_ids:
        if sid == payload.target_tag_id:
            continue  # Skip target if accidentally included
        tag = await tag_crud.get_tag(db, sid)
        if not tag:
            raise HTTPException(status_code=404, detail=f"Source tag {sid} not found")
        source_tags.append(tag)

    if not source_tags:
        return {"merged": 0, "message": "No source tags to merge"}

    merged_count = 0
    for source_tag in source_tags:
        # Get all photo-tag associations for source
        pt_result = await db.execute(
            sa_select(PhotoTag).where(PhotoTag.tag_id == source_tag.id)
        )
        photo_tags = pt_result.scalars().all()

        for pt in photo_tags:
            # Check if target tag already associated with this photo
            existing_result = await db.execute(
                sa_select(PhotoTag).where(
                    PhotoTag.photo_id == pt.photo_id,
                    PhotoTag.tag_id == target.id,
                )
            )
            if existing_result.scalar_one_or_none():
                # Already has target tag, just delete source association
                await db.delete(pt)
            else:
                # Re-associate to target
                pt.tag_id = target.id

        # Update target usage count
        target.usage_count = target.usage_count + source_tag.usage_count

        # Move aliases
        for alias in source_tag.aliases:
            alias.tag_id = target.id

        # Delete source tag
        await db.delete(source_tag)
        merged_count += 1

    await db.commit()

    return {
        "merged": merged_count,
        "target_tag": {"id": target.id, "name": target.name},
        "message": f"Merged {merged_count} tags into '{target.name}'",
    }


class TagBatchDeleteRequest(BaseModel):
    tag_ids: list[int] = Field(..., min_length=1, description="Tag IDs to delete")
    only_unused: bool = Field(default=True, description="Only delete tags with 0 usage")


@router.post("/batch-delete")
async def batch_delete_tags(
    payload: TagBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    """Batch delete tags. Safety: only deletes unused tags by default."""
    deleted = 0
    skipped = 0

    for tag_id in payload.tag_ids:
        tag = await tag_crud.get_tag(db, tag_id)
        if not tag:
            continue
        if payload.only_unused and tag.usage_count > 0:
            skipped += 1
            continue
        await tag_crud.delete_tag(db, tag)
        deleted += 1

    return {"deleted": deleted, "skipped": skipped}


@router.get("/categories")
async def get_tag_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get available tag categories with descriptions."""
    from app.services.tag_validation import TAG_CATEGORIES

    # Also get actual category distribution from DB
    cat_result = await db.execute(
        sa_select(Tag.category, func.count(Tag.id))
        .group_by(Tag.category)
    )
    db_categories = {row[0] or "uncategorized": row[1] for row in cat_result.all()}

    categories = []
    for key, info in TAG_CATEGORIES.items():
        categories.append({
            "key": key,
            "name": info["name"],
            "description": info["description"],
            "examples": info["examples"],
            "db_count": db_categories.get(key, 0),
        })

    # Add uncategorized
    categories.append({
        "key": "uncategorized",
        "name": "未分类",
        "description": "尚未分配类别的标签",
        "examples": [],
        "db_count": db_categories.get("uncategorized", 0),
    })

    return categories
