"""
CRUD operations for photos.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.photo import Photo
from app.models.tag import PhotoTag, Tag
from app.models.taxonomy import PhotoClassification, TaxonomyAlias, TaxonomyFacet, TaxonomyNode
from app.schemas.photo import PhotoUpdate

if TYPE_CHECKING:
    from app.services.search_interpreter import SearchInterpretation


def _photo_with_relations():
    return (
        selectinload(Photo.classifications).selectinload(PhotoClassification.facet),
        selectinload(Photo.classifications).selectinload(PhotoClassification.node),
        selectinload(Photo.tags),
    )


async def create_photo(
    db: AsyncSession,
    photo_data: dict,
    uploader_id: str,
) -> Photo:
    photo = Photo(uploader_id=uploader_id, **photo_data)
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo


async def get_photo(db: AsyncSession, photo_id: str) -> Optional[Photo]:
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    return result.scalar_one_or_none()


async def get_photo_with_tags(db: AsyncSession, photo_id: str) -> Optional[Photo]:
    result = await db.execute(
        select(Photo)
        .options(*_photo_with_relations())
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
    search: Optional[str] = None,
    tag: Optional[str] = None,
    exclude_categories: Optional[List[str]] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    campus: Optional[str] = None,
    building: Optional[str] = None,
    gallery_series: Optional[str] = None,
    gallery_year: Optional[str] = None,
    photo_type: Optional[str] = None,
    interpretation: Optional["SearchInterpretation"] = None,
) -> tuple[List[Photo], int]:
    query = select(Photo)
    count_query = select(func.count(Photo.id.distinct()))

    if uploader_id:
        query = query.where(Photo.uploader_id == uploader_id)
        count_query = count_query.where(Photo.uploader_id == uploader_id)

    if status:
        query = query.where(Photo.status == status)
        count_query = count_query.where(Photo.status == status)

    if season:
        season_subquery = (
            select(PhotoClassification.photo_id)
            .join(TaxonomyFacet, TaxonomyFacet.id == PhotoClassification.facet_id)
            .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
            .where(
                TaxonomyFacet.key == "season",
                TaxonomyNode.name == season,
            )
        )
        query = query.where(Photo.id.in_(season_subquery))
        count_query = count_query.where(Photo.id.in_(season_subquery))

    if category:
        query = query.where(Photo.category == category)
        count_query = count_query.where(Photo.category == category)

    if campus:
        campus_subquery = (
            select(PhotoClassification.photo_id)
            .join(TaxonomyFacet, TaxonomyFacet.id == PhotoClassification.facet_id)
            .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
            .where(
                TaxonomyFacet.key == "campus",
                TaxonomyNode.name == campus,
            )
        )
        query = query.where(Photo.id.in_(campus_subquery))
        count_query = count_query.where(Photo.id.in_(campus_subquery))

    if exclude_categories:
        for exc_cat in exclude_categories:
            query = query.where(Photo.category != exc_cat)
            count_query = count_query.where(Photo.category != exc_cat)

    if tag:
        tag_subquery = (
            select(PhotoTag.photo_id)
            .join(Tag)
            .where(Tag.name.ilike(f"%{tag.lower()}%"))
        )
        query = query.where(Photo.id.in_(tag_subquery))
        count_query = count_query.where(Photo.id.in_(tag_subquery))

    has_interpretation = interpretation and (interpretation.facet_filters or interpretation.keywords)

    facet_classification_filter = None
    if has_interpretation and interpretation.facet_filters:
        facet_classification_filter = _build_facet_classification_filter(interpretation)

    keyword_text_filter = None
    if has_interpretation and interpretation.keywords and not search:
        keyword_text_filter = _build_keyword_filter(interpretation.keywords)

    interp_filter = None
    if facet_classification_filter is not None and keyword_text_filter is not None:
        interp_filter = or_(facet_classification_filter, keyword_text_filter)
    elif facet_classification_filter is not None:
        interp_filter = facet_classification_filter
    elif keyword_text_filter is not None:
        interp_filter = keyword_text_filter

    text_filter = _build_text_search_filter(search) if search else None

    if interp_filter is not None and text_filter is not None:
        combined = or_(interp_filter, text_filter)
        query = query.where(combined)
        count_query = count_query.where(combined)
    elif interp_filter is not None:
        query = query.where(interp_filter)
        count_query = count_query.where(interp_filter)
    elif text_filter is not None:
        query = query.where(text_filter)
        count_query = count_query.where(text_filter)

    interpreted_facet_keys = set()
    if has_interpretation and interpretation.facet_filters:
        interpreted_facet_keys = set(interpretation.facet_filters.keys())

    facet_filters = {
        "landmark": building,
        "gallery_series": gallery_series,
        "gallery_year": gallery_year,
        "photo_type": photo_type,
    }
    for facet_key, facet_value in facet_filters.items():
        if not facet_value:
            continue
        if facet_key in interpreted_facet_keys:
            continue
        normalized_key = facet_value.lower().replace(" ", "-")
        classification_subquery = (
            select(PhotoClassification.photo_id)
            .join(TaxonomyFacet, TaxonomyFacet.id == PhotoClassification.facet_id)
            .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
            .where(
                TaxonomyFacet.key == facet_key,
                or_(
                    TaxonomyNode.name == facet_value,
                    TaxonomyNode.key == normalized_key,
                ),
            )
        )
        query = query.where(Photo.id.in_(classification_subquery))
        count_query = count_query.where(Photo.id.in_(classification_subquery))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    sort_column = getattr(Photo, sort_by, Photo.created_at)
    query = query.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query.options(*_photo_with_relations()))
    photos = result.scalars().all()
    return list(photos), total


async def update_photo(
    db: AsyncSession,
    photo: Photo,
    photo_update: PhotoUpdate,
) -> Photo:
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
    processed_path: Optional[str] = None,
) -> Photo:
    photo.processing_status = processing_status
    if processed_path:
        photo.processed_path = processed_path
    await db.commit()
    await db.refresh(photo)
    return photo


async def delete_photo(db: AsyncSession, photo: Photo) -> None:
    await db.delete(photo)
    await db.commit()


async def add_tags_to_photo(
    db: AsyncSession,
    photo_id: str,
    tag_ids: List[int],
) -> None:
    current_tags = await get_photo_tags(db, photo_id)
    for tag in current_tags:
        if tag.usage_count > 0:
            tag.usage_count -= 1

    await db.execute(PhotoTag.__table__.delete().where(PhotoTag.photo_id == photo_id))

    for tag_id in tag_ids:
        photo_tag = PhotoTag(photo_id=photo_id, tag_id=tag_id)
        db.add(photo_tag)
        tag = await db.get(Tag, tag_id)
        if tag:
            tag.usage_count += 1

    await db.commit()


async def get_photo_tags(db: AsyncSession, photo_id: str) -> List[Tag]:
    result = await db.execute(
        select(Tag)
        .join(PhotoTag)
        .where(PhotoTag.photo_id == photo_id)
    )
    return list(result.scalars().all())


def _build_facet_classification_filter(interpretation: "SearchInterpretation"):
    facet_subqueries = []
    for facet_key, node_name in interpretation.facet_filters.items():
        normalized_key = node_name.lower().replace(" ", "-")
        classification_subquery = (
            select(PhotoClassification.photo_id)
            .join(TaxonomyFacet, TaxonomyFacet.id == PhotoClassification.facet_id)
            .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
            .where(
                TaxonomyFacet.key == facet_key,
                or_(
                    TaxonomyNode.name == node_name,
                    TaxonomyNode.key == normalized_key,
                    TaxonomyNode.name.ilike(f"%{node_name}%"),
                ),
            )
        )
        facet_subqueries.append(Photo.id.in_(classification_subquery))
    if not facet_subqueries:
        return None
    return and_(*facet_subqueries) if len(facet_subqueries) > 1 else facet_subqueries[0]


def _build_keyword_filter(keywords: list[str]):
    keyword_filters = []
    for kw in keywords:
        pattern = f"%{kw}%"
        tag_sub = (
            select(PhotoTag.photo_id)
            .join(Tag)
            .where(Tag.name.ilike(pattern))
        )
        node_sub = (
            select(PhotoClassification.photo_id)
            .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
            .where(TaxonomyNode.name.ilike(pattern))
        )
        alias_sub = (
            select(PhotoClassification.photo_id)
            .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
            .join(TaxonomyAlias, TaxonomyAlias.node_id == TaxonomyNode.id)
            .where(TaxonomyAlias.alias.ilike(pattern))
        )
        keyword_filters.append(
            or_(
                Photo.filename.ilike(pattern),
                Photo.description.ilike(pattern),
                Photo.id.in_(tag_sub),
                Photo.id.in_(node_sub),
                Photo.id.in_(alias_sub),
            )
        )
    if not keyword_filters:
        return None
    return or_(*keyword_filters) if len(keyword_filters) > 1 else keyword_filters[0]


def _build_text_search_filter(search: str):
    search_pattern = f"%{search}%"
    tag_photo_subquery = (
        select(PhotoTag.photo_id)
        .join(Tag)
        .where(Tag.name.ilike(search_pattern))
    )
    taxonomy_node_subquery = (
        select(PhotoClassification.photo_id)
        .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
        .where(TaxonomyNode.name.ilike(search_pattern))
    )
    taxonomy_alias_subquery = (
        select(PhotoClassification.photo_id)
        .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
        .join(TaxonomyAlias, TaxonomyAlias.node_id == TaxonomyNode.id)
        .where(TaxonomyAlias.alias.ilike(search_pattern))
    )
    return or_(
        Photo.filename.ilike(search_pattern),
        Photo.description.ilike(search_pattern),
        Photo.id.in_(tag_photo_subquery),
        Photo.id.in_(taxonomy_node_subquery),
        Photo.id.in_(taxonomy_alias_subquery),
    )
