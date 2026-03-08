"""
Taxonomy service helpers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.photo import Photo
from app.models.taxonomy import PhotoClassification, TaxonomyAlias, TaxonomyFacet, TaxonomyNode

LEGACY_SEASON_MAP = {
    "春季": "Spring",
    "夏季": "Summer",
    "秋季": "Autumn",
    "冬季": "Winter",
}

LEGACY_PHOTO_TYPE_MAP = {
    "风光": "Landscape",
    "人像": "Portrait",
    "活动": "Activity",
    "纪实": "Documentary",
}

DEFAULT_TAXONOMY = [
    {
        "key": "season",
        "name": "季节",
        "is_system": True,
        "sort_order": 10,
        "nodes": ["春季", "夏季", "秋季", "冬季"],
    },
    {
        "key": "campus",
        "name": "校区",
        "is_system": True,
        "sort_order": 20,
        "nodes": ["昌平校区", "朝阳校区"],
    },
    {
        "key": "building",
        "name": "楼宇",
        "is_system": True,
        "sort_order": 30,
        "nodes": ["一教", "二教", "图书馆", "樱花苑学生公寓"],
    },
    {
        "key": "gallery_series",
        "name": "专题/赛事",
        "is_system": True,
        "sort_order": 40,
        "nodes": ["摄影大赛", "校园风光", "活动纪实"],
    },
    {
        "key": "gallery_year",
        "name": "年份",
        "is_system": True,
        "sort_order": 50,
        "nodes": [str(year) for year in range(2018, 2026)],
    },
    {
        "key": "photo_type",
        "name": "照片类型",
        "is_system": True,
        "sort_order": 60,
        "nodes": ["风光", "人像", "活动", "纪实"],
    },
]


def _node_key(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


async def ensure_default_taxonomy(db: AsyncSession) -> None:
    """Seed system facets and base nodes if they are missing."""
    for facet_seed in DEFAULT_TAXONOMY:
        result = await db.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == facet_seed["key"]))
        facet = result.scalar_one_or_none()
        if facet is None:
            facet = TaxonomyFacet(
                key=facet_seed["key"],
                name=facet_seed["name"],
                selection_mode="single",
                is_system=facet_seed.get("is_system", False),
                sort_order=facet_seed.get("sort_order", 0),
                is_active=True,
            )
            db.add(facet)
            await db.flush()

        existing_nodes_result = await db.execute(
            select(TaxonomyNode).where(TaxonomyNode.facet_id == facet.id)
        )
        existing_names = {node.name for node in existing_nodes_result.scalars().all()}
        for index, node_name in enumerate(facet_seed.get("nodes", []), start=1):
            if node_name in existing_names:
                continue
            db.add(
                TaxonomyNode(
                    facet_id=facet.id,
                    key=_node_key(node_name),
                    name=node_name,
                    sort_order=index,
                    is_active=True,
                )
            )

    await db.commit()


async def get_facets(db: AsyncSession, active_only: bool = False) -> list[TaxonomyFacet]:
    query = select(TaxonomyFacet).options(
        selectinload(TaxonomyFacet.nodes).selectinload(TaxonomyNode.aliases)
    ).order_by(TaxonomyFacet.sort_order.asc(), TaxonomyFacet.id.asc())
    if active_only:
        query = query.where(TaxonomyFacet.is_active.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


def build_node_tree(nodes: list[TaxonomyNode]) -> list[TaxonomyNode]:
    """Convert a flat node list into a nested tree in-memory."""
    node_map = {node.id: node for node in nodes}
    roots: list[TaxonomyNode] = []
    for node in nodes:
        node.children = []
    for node in nodes:
        if node.parent_id and node.parent_id in node_map:
            node_map[node.parent_id].children.append(node)
        else:
            roots.append(node)
    for node in node_map.values():
        node.children.sort(key=lambda child: (child.sort_order, child.id))
    roots.sort(key=lambda item: (item.sort_order, item.id))
    return roots


async def get_facet_by_id(db: AsyncSession, facet_id: int) -> Optional[TaxonomyFacet]:
    result = await db.execute(
        select(TaxonomyFacet)
        .options(selectinload(TaxonomyFacet.nodes).selectinload(TaxonomyNode.aliases))
        .where(TaxonomyFacet.id == facet_id)
    )
    return result.scalar_one_or_none()


async def get_facet_by_key(db: AsyncSession, facet_key: str) -> Optional[TaxonomyFacet]:
    result = await db.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == facet_key))
    return result.scalar_one_or_none()


async def get_node_by_id(db: AsyncSession, node_id: int) -> Optional[TaxonomyNode]:
    result = await db.execute(
        select(TaxonomyNode)
        .options(selectinload(TaxonomyNode.aliases))
        .where(TaxonomyNode.id == node_id)
    )
    return result.scalar_one_or_none()


async def replace_node_aliases(db: AsyncSession, node: TaxonomyNode, aliases: list[str]) -> None:
    await db.execute(TaxonomyAlias.__table__.delete().where(TaxonomyAlias.node_id == node.id))
    for alias in aliases:
        clean = alias.strip()
        if clean:
            db.add(TaxonomyAlias(node_id=node.id, alias=clean))


async def resolve_taxonomy_node(
    db: AsyncSession,
    facet_key: str,
    raw_value: str,
) -> Optional[TaxonomyNode]:
    clean = raw_value.strip()
    facet = await get_facet_by_key(db, facet_key)
    if facet is None:
        return None

    result = await db.execute(
        select(TaxonomyNode)
        .where(
            TaxonomyNode.facet_id == facet.id,
            func.lower(TaxonomyNode.name) == clean.lower(),
        )
    )
    node = result.scalar_one_or_none()
    if node:
        return node

    result = await db.execute(
        select(TaxonomyNode)
        .where(
            TaxonomyNode.facet_id == facet.id,
            func.lower(TaxonomyNode.key) == _node_key(clean),
        )
    )
    node = result.scalar_one_or_none()
    if node:
        return node

    result = await db.execute(
        select(TaxonomyNode)
        .join(TaxonomyAlias)
        .where(
            TaxonomyNode.facet_id == facet.id,
            func.lower(TaxonomyAlias.alias) == clean.lower(),
        )
    )
    return result.scalar_one_or_none()


async def set_photo_classification(
    db: AsyncSession,
    photo: Photo,
    facet_key: str,
    node: TaxonomyNode,
) -> None:
    facet = await get_facet_by_key(db, facet_key)
    if facet is None:
        raise ValueError(f"Unknown facet: {facet_key}")

    result = await db.execute(
        select(PhotoClassification).where(
            PhotoClassification.photo_id == photo.id,
            PhotoClassification.facet_id == facet.id,
        )
    )
    classification = result.scalar_one_or_none()
    now = datetime.utcnow()
    if classification is None:
        classification = PhotoClassification(
            photo_id=photo.id,
            facet_id=facet.id,
            node_id=node.id,
            created_at=now,
            updated_at=now,
        )
        db.add(classification)
    else:
        classification.node_id = node.id
        classification.updated_at = now

    if facet_key == "season":
        photo.season = LEGACY_SEASON_MAP.get(node.name, node.name)
    elif facet_key == "campus":
        photo.campus = node.name
    elif facet_key == "photo_type":
        photo.category = LEGACY_PHOTO_TYPE_MAP.get(node.name, node.name)


def build_node_path(node: TaxonomyNode) -> list[str]:
    path: list[str] = []
    current = node
    while current is not None:
        path.insert(0, current.name)
        current = current.parent
    return path


def serialize_classifications(photo: Photo) -> dict[str, dict[str, object]]:
    values: dict[str, dict[str, object]] = {}
    for classification in getattr(photo, "classifications", []) or []:
        if not classification.facet or not classification.node:
            continue
        values[classification.facet.key] = {
            "facet_key": classification.facet.key,
            "facet_name": classification.facet.name,
            "node_id": classification.node.id,
            "node_key": classification.node.key,
            "node_name": classification.node.name,
            "path": build_node_path(classification.node),
        }
    return values
