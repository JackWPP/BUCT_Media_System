"""
Taxonomy management endpoints.
"""
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_auditor_user, get_db
from app.models.photo import Photo
from app.models.taxonomy import PhotoClassification, TaxonomyAlias, TaxonomyFacet, TaxonomyNode
from app.models.user import User
from app.schemas.taxonomy import (
    TaxonomyFacetCreate,
    TaxonomyFacetResponse,
    TaxonomyFacetUpdate,
    TaxonomyNodeCreate,
    TaxonomyNodeResponse,
    TaxonomyNodeUpdate,
)
from app.services.taxonomy import (
    TAXONOMY_GUIDE,
    build_node_tree,
    ensure_default_taxonomy,
    get_facet_by_id,
    get_facets,
    get_node_by_id,
    replace_node_aliases,
)

router = APIRouter()


class TaxonomyFacetInsight(BaseModel):
    facet_key: str
    facet_name: str
    node_name: str
    count: int


class UnclassifiedPhotoItem(BaseModel):
    id: str
    filename: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class TaxonomyInsightsResponse(BaseModel):
    unclassified_total: int
    unclassified_items: list[UnclassifiedPhotoItem]
    facet_counts: list[TaxonomyFacetInsight]


def _serialize_facet(facet: TaxonomyFacet) -> TaxonomyFacetResponse:
    nodes = list(facet.nodes or [])
    for node in nodes:
        node.children = []
    facet.nodes = build_node_tree(nodes)
    return TaxonomyFacetResponse.model_validate(facet)


def _serialize_node(node: TaxonomyNode) -> TaxonomyNodeResponse:
    """Serialize a taxonomy node without triggering async lazy loads."""
    unloaded = inspect(node).unloaded
    aliases = [] if "aliases" in unloaded else list(node.aliases or [])
    children = [] if "children" in unloaded else list(node.children or [])
    return TaxonomyNodeResponse(
        id=node.id,
        facet_id=node.facet_id,
        parent_id=node.parent_id,
        key=node.key,
        name=node.name,
        description=node.description,
        sort_order=node.sort_order,
        is_active=node.is_active,
        is_selectable=node.is_selectable,
        created_at=node.created_at,
        updated_at=node.updated_at,
        aliases=aliases,
        children=[_serialize_node(child) for child in children],
    )


async def _validate_node_parent(db: AsyncSession, facet_id: int, parent_id: int | None) -> None:
    if parent_id is None:
        return
    parent = await get_node_by_id(db, parent_id)
    if parent is None:
        raise HTTPException(status_code=400, detail="Parent node not found")
    if parent.facet_id != facet_id:
        raise HTTPException(status_code=400, detail="Parent node must belong to the same facet")


async def _assert_node_key_available(
    db: AsyncSession,
    facet_id: int,
    key: str,
    *,
    exclude_node_id: int | None = None,
) -> None:
    query = select(TaxonomyNode.id).where(TaxonomyNode.facet_id == facet_id, TaxonomyNode.key == key)
    if exclude_node_id is not None:
        query = query.where(TaxonomyNode.id != exclude_node_id)
    exists = await db.execute(query.limit(1))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Node key already exists in this facet")


async def _assert_aliases_available(
    db: AsyncSession,
    aliases: list[str],
    *,
    exclude_node_id: int | None = None,
) -> list[str]:
    cleaned = [alias.strip() for alias in aliases if alias.strip()]
    if len(cleaned) != len(set(cleaned)):
        raise HTTPException(status_code=400, detail="Aliases must be unique")
    if not cleaned:
        return cleaned

    query = select(TaxonomyAlias.alias).where(TaxonomyAlias.alias.in_(cleaned))
    if exclude_node_id is not None:
        query = query.where(TaxonomyAlias.node_id != exclude_node_id)
    existing = [row[0] for row in (await db.execute(query)).all()]
    if existing:
        raise HTTPException(status_code=409, detail=f"Alias already exists: {', '.join(existing)}")
    return cleaned


@router.get("/public", response_model=list[TaxonomyFacetResponse])
async def list_public_taxonomy(
    db: AsyncSession = Depends(get_db),
):
    facets = await get_facets(db, active_only=True)
    return [_serialize_facet(facet) for facet in facets]


@router.get("/public/guide")
async def get_public_taxonomy_guide(
    db: AsyncSession = Depends(get_db),
):
    return TAXONOMY_GUIDE


@router.get("/facets", response_model=list[TaxonomyFacetResponse])
async def list_taxonomy_facets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    await ensure_default_taxonomy(db)
    await db.commit()
    facets = await get_facets(db, active_only=True)
    return [_serialize_facet(facet) for facet in facets]


@router.get("/insights", response_model=TaxonomyInsightsResponse)
async def get_taxonomy_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    await ensure_default_taxonomy(db)
    await db.commit()

    facet_count_rows = await db.execute(
        select(
            TaxonomyFacet.key,
            TaxonomyFacet.name,
            TaxonomyNode.name,
            func.count(PhotoClassification.photo_id),
        )
        .select_from(TaxonomyFacet)
        .join(TaxonomyNode, TaxonomyNode.facet_id == TaxonomyFacet.id)
        .join(PhotoClassification, PhotoClassification.node_id == TaxonomyNode.id)
        .where(TaxonomyFacet.is_active.is_(True), TaxonomyNode.is_active.is_(True))
        .group_by(TaxonomyFacet.key, TaxonomyFacet.name, TaxonomyFacet.sort_order, TaxonomyNode.name, TaxonomyNode.sort_order)
        .order_by(TaxonomyFacet.sort_order.asc(), func.count(PhotoClassification.photo_id).desc(), TaxonomyNode.sort_order.asc())
    )

    unclassified_exists = (
        select(PhotoClassification.id)
        .where(PhotoClassification.photo_id == Photo.id)
        .correlate(Photo)
        .exists()
    )
    unclassified_base = select(Photo).where(~unclassified_exists)

    unclassified_items_result = await db.execute(
        unclassified_base.order_by(Photo.created_at.desc()).limit(10)
    )
    unclassified_total_result = await db.execute(
        select(func.count()).select_from(
            unclassified_base.with_only_columns(Photo.id).subquery()
        )
    )

    return TaxonomyInsightsResponse(
        unclassified_total=unclassified_total_result.scalar_one(),
        unclassified_items=[
            UnclassifiedPhotoItem(id=item.id, filename=item.filename, status=item.status)
            for item in unclassified_items_result.scalars().all()
        ],
        facet_counts=[
            TaxonomyFacetInsight(
                facet_key=facet_key,
                facet_name=facet_name,
                node_name=node_name,
                count=count,
            )
            for facet_key, facet_name, node_name, count in facet_count_rows.all()
        ],
    )


@router.post("/facets", response_model=TaxonomyFacetResponse, status_code=status.HTTP_201_CREATED)
async def create_taxonomy_facet(
    facet_in: TaxonomyFacetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    facet = TaxonomyFacet(**facet_in.model_dump())
    db.add(facet)
    await db.commit()
    await db.refresh(facet)
    facet = await get_facet_by_id(db, facet.id)
    return _serialize_facet(facet)


@router.get("/facets/{facet_id}", response_model=TaxonomyFacetResponse)
async def get_taxonomy_facet(
    facet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    facet = await get_facet_by_id(db, facet_id)
    if facet is None:
        raise HTTPException(status_code=404, detail="Facet not found")
    return _serialize_facet(facet)


@router.patch("/facets/{facet_id}", response_model=TaxonomyFacetResponse)
async def update_taxonomy_facet(
    facet_id: int,
    facet_update: TaxonomyFacetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    facet = await get_facet_by_id(db, facet_id)
    if facet is None:
        raise HTTPException(status_code=404, detail="Facet not found")
    for field, value in facet_update.model_dump(exclude_unset=True).items():
        setattr(facet, field, value)
    await db.commit()
    await db.refresh(facet)
    facet = await get_facet_by_id(db, facet.id)
    return _serialize_facet(facet)


@router.post("/facets/{facet_id}/nodes", response_model=TaxonomyNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_taxonomy_node(
    facet_id: int,
    node_in: TaxonomyNodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    facet = await get_facet_by_id(db, facet_id)
    if facet is None:
        raise HTTPException(status_code=404, detail="Facet not found")
    await _validate_node_parent(db, facet.id, node_in.parent_id)
    await _assert_node_key_available(db, facet.id, node_in.key)
    cleaned_aliases = await _assert_aliases_available(db, node_in.aliases)

    node = TaxonomyNode(
        facet_id=facet.id,
        key=node_in.key,
        name=node_in.name,
        description=node_in.description,
        parent_id=node_in.parent_id,
        sort_order=node_in.sort_order,
        is_active=node_in.is_active,
        is_selectable=node_in.is_selectable,
    )
    try:
        db.add(node)
        await db.flush()
        await replace_node_aliases(db, node, cleaned_aliases)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Taxonomy node key or alias already exists") from exc
    node = await get_node_by_id(db, node.id)
    return _serialize_node(node)


@router.patch("/nodes/{node_id}", response_model=TaxonomyNodeResponse)
async def update_taxonomy_node(
    node_id: int,
    node_update: TaxonomyNodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    node = await get_node_by_id(db, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")

    update_data = node_update.model_dump(exclude_unset=True, exclude={"aliases"})
    if "parent_id" in update_data:
        await _validate_node_parent(db, node.facet_id, update_data["parent_id"])
    if "key" in update_data:
        await _assert_node_key_available(db, node.facet_id, update_data["key"], exclude_node_id=node.id)
    cleaned_aliases = None
    if node_update.aliases is not None:
        cleaned_aliases = await _assert_aliases_available(db, node_update.aliases, exclude_node_id=node.id)
    for field, value in update_data.items():
        setattr(node, field, value)
    try:
        if cleaned_aliases is not None:
            await replace_node_aliases(db, node, cleaned_aliases)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Taxonomy node key or alias already exists") from exc
    node = await get_node_by_id(db, node.id)
    return _serialize_node(node)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_taxonomy_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    node = await get_node_by_id(db, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    await db.delete(node)
    await db.commit()
    return None
