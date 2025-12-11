"""
Tag API endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.tag import TagCreate, TagUpdate, TagResponse, TagListResponse
from app.crud import tag as tag_crud


router = APIRouter()


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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get popular tags sorted by usage count
    
    - **limit**: Maximum number of tags to return (max 50)
    """
    limit = min(limit, 50)
    
    tags = await tag_crud.get_popular_tags(db, limit=limit)
    
    return [TagResponse.model_validate(tag) for tag in tags]


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new tag
    
    Only admins can create tags manually
    """
    # Check admin permission
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create tags"
        )
    
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
    current_user: User = Depends(get_current_user)
):
    """
    Update a tag
    
    Only admins can update tags
    """
    # Check admin permission
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update tags"
        )
    
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
    current_user: User = Depends(get_current_user)
):
    """
    Delete a tag
    
    Only admins can delete tags
    Note: This will also remove all photo-tag associations
    """
    # Check admin permission
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete tags"
        )
    
    tag = await tag_crud.get_tag(db, tag_id)
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    await tag_crud.delete_tag(db, tag)
    
    return None
