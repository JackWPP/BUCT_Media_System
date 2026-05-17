"""
CRUD operations for Tag
"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag, TagAlias
from app.schemas.tag import TagCreate, TagUpdate
from app.services.tag_normalization import normalize_tag_name, resolve_tag_by_name_or_alias


async def create_tag(
    db: AsyncSession,
    tag: TagCreate
) -> Tag:
    """
    Create a new tag
    
    Args:
        db: Database session
        tag: Tag creation data
    
    Returns:
        Created Tag object
    """
    # Convert name to lowercase for consistency
    db_tag = Tag(
        name=normalize_tag_name(tag.name),
        category=tag.category,
        color=tag.color or _generate_random_color()
    )
    db.add(db_tag)
    await db.commit()
    await db.refresh(db_tag)
    return db_tag


async def get_tag(db: AsyncSession, tag_id: int) -> Optional[Tag]:
    """
    Get a tag by ID
    
    Args:
        db: Database session
        tag_id: Tag ID
    
    Returns:
        Tag object or None
    """
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id)
    )
    return result.scalar_one_or_none()


async def get_tag_by_name(db: AsyncSession, name: str) -> Optional[Tag]:
    """
    Get a tag by name (case-insensitive)
    
    Args:
        db: Database session
        name: Tag name
    
    Returns:
        Tag object or None
    """
    result = await db.execute(
        select(Tag).where(Tag.name == normalize_tag_name(name))
    )
    return result.scalar_one_or_none()


async def get_tags(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category: Optional[str] = None
) -> tuple[List[Tag], int]:
    """
    Get tags with filtering and pagination
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Search in tag name
        category: Filter by category
    
    Returns:
        Tuple of (list of tags, total count)
    """
    query = select(Tag)
    count_query = select(func.count(Tag.id))
    
    # Apply filters
    if search:
        search_pattern = f"%{normalize_tag_name(search)}%"
        search_filter = Tag.name.ilike(search_pattern)
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    if category:
        query = query.where(Tag.category == category)
        count_query = count_query.where(Tag.category == category)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Apply ordering and pagination
    query = query.order_by(Tag.usage_count.desc(), Tag.name).offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    tags = result.scalars().all()
    
    return list(tags), total


async def get_popular_tags(
    db: AsyncSession,
    limit: int = 20
) -> List[Tag]:
    """
    Get popular tags sorted by usage count
    
    Args:
        db: Database session
        limit: Maximum number of tags to return
    
    Returns:
        List of popular tags
    """
    result = await db.execute(
        select(Tag)
        .where(Tag.usage_count > 0)
        .order_by(Tag.usage_count.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_tag(
    db: AsyncSession,
    tag: Tag,
    tag_update: TagUpdate
) -> Tag:
    """
    Update a tag
    
    Args:
        db: Database session
        tag: Tag object to update
        tag_update: Update data
    
    Returns:
        Updated Tag object
    """
    update_data = tag_update.model_dump(exclude_unset=True)
    
    # Convert name to lowercase if provided
    if 'name' in update_data:
        update_data['name'] = normalize_tag_name(update_data['name'])
    
    for field, value in update_data.items():
        setattr(tag, field, value)
    
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag: Tag) -> None:
    """
    Delete a tag
    
    Args:
        db: Database session
        tag: Tag object to delete
    """
    await db.delete(tag)
    await db.commit()


async def get_or_create_tag(
    db: AsyncSession,
    name: str,
    category: Optional[str] = None
) -> Tag:
    """
    Get an existing tag by name or create a new one
    
    Args:
        db: Database session
        name: Tag name
        category: Tag category (optional)
    
    Returns:
        Tag object (existing or newly created)
    """
    # Try to find existing tag
    tag = await resolve_tag_by_name_or_alias(db, name)
    
    if tag:
        return tag
    
    # Create new tag if not found
    new_tag = Tag(
        name=normalize_tag_name(name),
        category=category,
        color=_generate_random_color()
    )
    db.add(new_tag)
    await db.commit()
    await db.refresh(new_tag)
    return new_tag


async def get_tag_suggestions(
    db: AsyncSession,
    query: str,
    limit: int = 12,
) -> list[dict]:
    clean = normalize_tag_name(query)
    if not clean:
        return []
    pattern = f"%{clean}%"
    rows = await db.execute(
        select(Tag, TagAlias.alias)
        .outerjoin(TagAlias)
        .where((Tag.name.ilike(pattern)) | (TagAlias.alias.ilike(pattern)))
        .order_by(Tag.usage_count.desc(), Tag.name.asc())
        .limit(limit)
    )
    seen: set[int] = set()
    suggestions: list[dict] = []
    for tag, alias in rows.all():
        if tag.id in seen:
            continue
        seen.add(tag.id)
        suggestions.append(
            {
                "id": tag.id,
                "name": tag.name,
                "category": tag.category,
                "color": tag.color,
                "usage_count": tag.usage_count,
                "matched_alias": alias if alias and clean in alias.lower() and alias != tag.name else None,
            }
        )
    return suggestions


def _generate_random_color() -> str:
    """
    Generate a random HEX color code
    
    Returns:
        HEX color string (e.g., '#3B82F6')
    """
    import random
    
    # Predefined color palette for better aesthetics
    colors = [
        '#3B82F6',  # Blue
        '#10B981',  # Green
        '#F59E0B',  # Orange
        '#EF4444',  # Red
        '#8B5CF6',  # Purple
        '#EC4899',  # Pink
        '#14B8A6',  # Teal
        '#F97316',  # Deep Orange
        '#6366F1',  # Indigo
        '#84CC16',  # Lime
    ]
    
    return random.choice(colors)
