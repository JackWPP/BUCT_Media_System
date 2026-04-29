"""
Taxonomy management endpoints.
"""
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_auditor_user, get_db
from app.models.photo import Photo
from app.models.taxonomy import PhotoClassification, TaxonomyFacet, TaxonomyNode
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


@router.get("/public", response_model=list[TaxonomyFacetResponse])
async def list_public_taxonomy(
    db: AsyncSession = Depends(get_db),
):
    await ensure_default_taxonomy(db)
    await db.commit()
    facets = await get_facets(db, active_only=True)
    return [_serialize_facet(facet) for facet in facets]


@router.get("/facets", response_model=list[TaxonomyFacetResponse])
async def list_taxonomy_facets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_auditor_user),
):
    await ensure_default_taxonomy(db)
    await db.commit()
    facets = await get_facets(db, active_only=False)
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
            func.count(Photo.id),
        )
        .join(TaxonomyNode, TaxonomyNode.facet_id == TaxonomyFacet.id)
        .join(TaxonomyNode.photo_classifications)
        .join(Photo)
        .group_by(TaxonomyFacet.key, TaxonomyFacet.name, TaxonomyNode.name)
        .order_by(TaxonomyFacet.sort_order.asc(), func.count(Photo.id).desc(), TaxonomyNode.sort_order.asc())
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

    node = TaxonomyNode(
        facet_id=facet.id,
        key=node_in.key,
        name=node_in.name,
        description=node_in.description,
        parent_id=node_in.parent_id,
        sort_order=node_in.sort_order,
        is_active=node_in.is_active,
    )
    db.add(node)
    await db.flush()
    await replace_node_aliases(db, node, node_in.aliases)
    await db.commit()
    node = await get_node_by_id(db, node.id)
    return TaxonomyNodeResponse.model_validate(node)


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
    for field, value in update_data.items():
        setattr(node, field, value)
    if node_update.aliases is not None:
        await replace_node_aliases(db, node, node_update.aliases)
    await db.commit()
    node = await get_node_by_id(db, node.id)
    return TaxonomyNodeResponse.model_validate(node)


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
