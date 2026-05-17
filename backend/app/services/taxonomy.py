"""
Taxonomy service helpers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria

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
    "风光类": "Landscape",
    "人像": "Portrait",
    "活动": "Activity",
    "纪实": "Documentary",
    "纪实类": "Documentary",
}

DEFAULT_TAXONOMY = [
    {
        "key": "season",
        "name": "季节",
        "is_system": True,
        "sort_order": 10,
        "nodes": ["春季", "夏季", "秋季", "冬季"],
        "aliases": {
            "春季": ["春天", "春日", "春"],
            "夏季": ["夏天", "夏日", "夏"],
            "秋季": ["秋天", "秋日", "秋", "金秋"],
            "冬季": ["冬天", "冬日", "冬"],
        },
    },
    {
        "key": "campus",
        "name": "校区",
        "is_system": True,
        "sort_order": 20,
        "nodes": ["朝阳校区", "昌平校区", "海淀校区"],
        "aliases": {
            "昌平校区": ["昌平", "北化昌平"],
            "朝阳校区": ["朝阳", "北化朝阳"],
            "海淀校区": ["海淀", "北化海淀"],
        },
    },
    {
        "key": "landmark",
        "name": "建筑/地点",
        "is_system": True,
        "sort_order": 30,
        "nodes": [
            "第一教学楼", "体育馆", "图书馆", "第二教学楼", "大学生活动中心",
            "文理楼", "实验楼", "工程训练中心", "校史博物馆", "机电信息楼A座",
            "学生公寓", "紫竹餐厅", "玉兰餐厅", "后勤服务楼", "新校区建设指挥部",
            "柳湖", "玉屏山", "校名石", "运动场", "其它",
        ],
        "aliases": {
            "图书馆": ["北化图书馆", "新图书馆"],
            "大学生活动中心": ["学生活动中心", "活动中心", "学生中心"],
            "柳湖": ["湖", "校园湖", "学校湖"],
            "第一教学楼": ["一教"],
            "第二教学楼": ["二教"],
            "实验楼": ["实验中心", "综合实验楼"],
            "体育馆": ["体育中心", "室内体育馆"],
            "运动场": ["操场", "体育场"],
            "学生公寓": ["宿舍", "学生宿舍", "樱花苑学生公寓", "樱花苑", "樱花苑公寓"],
            "其它": ["其他", "三教", "第三教学楼", "行政楼", "主楼", "科技大厦", "樱花大道", "校门", "主楼广场"],
        },
    },
    {
        "key": "gallery_series",
        "name": "专区",
        "is_system": True,
        "sort_order": 40,
        "nodes": ["昌平校区摄影大赛", "师生投稿"],
        "aliases": {
            "昌平校区摄影大赛": ["摄影大赛", "摄影比赛", "摄影大赛作品", "昌平摄影大赛"],
            "师生投稿": ["学生投稿", "教师投稿", "师生作品"],
        },
    },
    {
        "key": "gallery_year",
        "name": "届次/年份",
        "is_system": True,
        "sort_order": 50,
        "nodes": [
            "2018年第一届获奖作品",
            "2019年第二届获奖作品",
            "2020年第三届获奖作品",
            "2021年第四届获奖作品",
            "2022年第五届获奖作品",
            "2023年第六届获奖作品",
            "2024年第七届获奖作品",
            "2025年第八届获奖作品",
        ],
        "aliases": {
            "2018年第一届获奖作品": ["2018", "2018年", "第一届"],
            "2019年第二届获奖作品": ["2019", "2019年", "第二届"],
            "2020年第三届获奖作品": ["2020", "2020年", "第三届"],
            "2021年第四届获奖作品": ["2021", "2021年", "第四届"],
            "2022年第五届获奖作品": ["2022", "2022年", "第五届"],
            "2023年第六届获奖作品": ["2023", "2023年", "第六届"],
            "2024年第七届获奖作品": ["2024", "2024年", "第七届"],
            "2025年第八届获奖作品": ["2025", "2025年", "第八届"],
        },
    },
    {
        "key": "award_level",
        "name": "奖项",
        "is_system": True,
        "sort_order": 55,
        "nodes": ["特等奖", "一等奖", "二等奖", "优秀奖"],
        "aliases": {},
    },
    {
        "key": "photo_type",
        "name": "类别",
        "is_system": True,
        "sort_order": 60,
        "nodes": ["风光类", "纪实类"],
        "aliases": {
            "风光类": ["风光", "风景", "风景照", "自然风光", "景色", "风光摄影", "Landscape"],
            "纪实类": ["纪实", "活动", "记录", "纪实摄影", "记录片", "Documentary", "Activity"],
        },
    },
    {
        "key": "documentary_topic",
        "name": "纪实主题",
        "is_system": True,
        "sort_order": 70,
        "nodes": [
            "德育", "智育", "体育", "美育", "劳育",
            "春季百花节", "夏季荷花节", "秋季山楂节", "秋季枫叶节", "冬季冰雪节",
            "接待会议", "大型活动", "其他",
        ],
        "aliases": {
            "接待会议": ["会议", "接待"],
            "大型活动": ["校园活动"],
        },
    },
]

LEGACY_NODE_MERGES = {
    "landmark": {
        "一教": "第一教学楼",
        "二教": "第二教学楼",
        "三教": "其它",
        "行政楼": "其它",
        "主楼": "其它",
        "科技大厦": "其它",
        "樱花苑学生公寓": "学生公寓",
        "学生活动中心": "大学生活动中心",
        "樱花大道": "其它",
        "操场": "运动场",
        "校门": "其它",
        "主楼广场": "其它",
    },
    "gallery_series": {
        "摄影大赛": "昌平校区摄影大赛",
        "校园风光": "师生投稿",
        "活动纪实": "师生投稿",
    },
    "gallery_year": {
        "2018": "2018年第一届获奖作品",
        "2019": "2019年第二届获奖作品",
        "2020": "2020年第三届获奖作品",
        "2021": "2021年第四届获奖作品",
        "2022": "2022年第五届获奖作品",
        "2023": "2023年第六届获奖作品",
        "2024": "2024年第七届获奖作品",
        "2025": "2025年第八届获奖作品",
    },
    "photo_type": {
        "风光": "风光类",
        "纪实": "纪实类",
        "活动": "纪实类",
        "人像": None,
    },
}

TAXONOMY_GUIDE = {
    "primary": ["gallery_series", "campus", "photo_type"],
    "dependencies": {
        "campus": {"昌平校区": ["landmark"]},
        "gallery_series": {"昌平校区摄影大赛": ["gallery_year", "award_level"]},
        "photo_type": {"风光类": ["season"], "纪实类": ["documentary_topic"]},
    },
    "legacy_query_aliases": {"building": "landmark"},
}


def _node_key(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


async def ensure_default_taxonomy(db: AsyncSession) -> None:
    """Seed system facets, base nodes, and aliases if they are missing.

    Uses flush instead of commit so the caller controls the transaction boundary.
    """
    created = False
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
            created = True
        else:
            facet.name = facet_seed["name"]
            facet.selection_mode = "single"
            facet.is_system = facet_seed.get("is_system", facet.is_system)
            facet.sort_order = facet_seed.get("sort_order", facet.sort_order)
            facet.is_active = True

        existing_nodes_result = await db.execute(
            select(TaxonomyNode).where(TaxonomyNode.facet_id == facet.id)
        )
        existing_nodes = {node.name: node for node in existing_nodes_result.scalars().all()}
        for index, node_name in enumerate(facet_seed.get("nodes", []), start=1):
            if node_name in existing_nodes:
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
            created = True

        await db.flush()

        aliases_map = facet_seed.get("aliases", {})
        if aliases_map:
            nodes_result = await db.execute(
                select(TaxonomyNode).where(TaxonomyNode.facet_id == facet.id)
            )
            all_nodes = {node.name: node for node in nodes_result.scalars().all()}

            for node_name, alias_list in aliases_map.items():
                node = all_nodes.get(node_name)
                if node is None:
                    continue
                existing_aliases_result = await db.execute(
                    select(TaxonomyAlias.alias).where(TaxonomyAlias.node_id == node.id)
                )
                existing_aliases = {row[0] for row in existing_aliases_result.all()}
                for alias in alias_list:
                    clean = alias.strip()
                    if not clean or clean == node.name or clean in existing_aliases:
                        continue
                    alias_result = await db.execute(
                        select(TaxonomyAlias).where(TaxonomyAlias.alias == clean)
                    )
                    existing_alias = alias_result.scalar_one_or_none()
                    if existing_alias is None:
                        db.add(TaxonomyAlias(node_id=node.id, alias=clean))
                        created = True
                    elif existing_alias.node_id != node.id:
                        existing_alias.node_id = node.id
                        created = True

        if await reconcile_facet_to_seed(db, facet, facet_seed):
            created = True

    if created:
        await db.flush()


async def reconcile_facet_to_seed(db: AsyncSession, facet: TaxonomyFacet, facet_seed: dict) -> bool:
    """Converge an existing facet to the new controlled vocabulary.

    Old nodes are not exposed publicly after this. Where a confident mapping
    exists, photo classifications are moved to the new node first.
    """
    changed = False
    allowed_names = set(facet_seed.get("nodes", []))
    merge_map = LEGACY_NODE_MERGES.get(facet.key, {})

    result = await db.execute(select(TaxonomyNode).where(TaxonomyNode.facet_id == facet.id))
    nodes = list(result.scalars().all())
    nodes_by_name = {node.name: node for node in nodes}

    for source_name, target_name in merge_map.items():
        source = nodes_by_name.get(source_name)
        if source is None or target_name is None:
            continue
        target = nodes_by_name.get(target_name)
        if target is None:
            continue
        classifications_result = await db.execute(
            select(PhotoClassification).where(PhotoClassification.node_id == source.id)
        )
        for classification in classifications_result.scalars().all():
            existing_result = await db.execute(
                select(PhotoClassification).where(
                    PhotoClassification.photo_id == classification.photo_id,
                    PhotoClassification.facet_id == classification.facet_id,
                    PhotoClassification.node_id == target.id,
                )
            )
            if existing_result.scalar_one_or_none() is None:
                classification.node_id = target.id
                classification.updated_at = datetime.utcnow()
            else:
                await db.delete(classification)
            changed = True

    for index, node_name in enumerate(facet_seed.get("nodes", []), start=1):
        node = nodes_by_name.get(node_name)
        if node is not None:
            if node.sort_order != index:
                node.sort_order = index
                changed = True
            if not node.is_active:
                node.is_active = True
                changed = True

    for node in nodes:
        if node.name not in allowed_names and node.is_active:
            node.is_active = False
            changed = True

    return changed


async def get_facets(db: AsyncSession, active_only: bool = False) -> list[TaxonomyFacet]:
    options = [
        selectinload(TaxonomyFacet.nodes).options(
            selectinload(TaxonomyNode.aliases),
            selectinload(TaxonomyNode.children),
        )
    ]
    if active_only:
        options.append(
            with_loader_criteria(
                TaxonomyNode,
                TaxonomyNode.is_active.is_(True),
                include_aliases=True,
            )
        )
    query = select(TaxonomyFacet).options(*options).order_by(TaxonomyFacet.sort_order.asc(), TaxonomyFacet.id.asc())
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
            TaxonomyNode.is_active.is_(True),
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
            TaxonomyNode.is_active.is_(True),
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
            TaxonomyNode.is_active.is_(True),
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
    if not node.is_active:
        raise ValueError(f"Inactive taxonomy node cannot be assigned: {node.name}")

    facet = await get_facet_by_key(db, facet_key)
    if facet is None:
        raise ValueError(f"Unknown facet: {facet_key}")
    if node.facet_id != facet.id:
        raise ValueError(f"Node {node.id} does not belong to facet: {facet_key}")

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


async def set_photo_classifications(
    db: AsyncSession,
    photo: Photo,
    classifications: dict[str, int],
) -> None:
    """Batch set classifications for a photo: { facet_key: node_id }."""
    for facet_key, node_id in classifications.items():
        node = await get_node_by_id(db, node_id)
        if node is None:
            raise ValueError(f"Unknown node id: {node_id}")
        await set_photo_classification(db, photo, facet_key, node)


async def delete_photo_classification(
    db: AsyncSession,
    photo: Photo,
    facet_key: str,
) -> None:
    """Remove a classification for a single facet from a photo."""
    facet = await get_facet_by_key(db, facet_key)
    if facet is None:
        raise HTTPException(status_code=404, detail=f"Unknown facet: {facet_key}")

    result = await db.execute(
        select(PhotoClassification).where(
            PhotoClassification.photo_id == photo.id,
            PhotoClassification.facet_id == facet.id,
        )
    )
    classification = result.scalar_one_or_none()
    if classification is None:
        return

    await db.delete(classification)

    if facet_key == "season":
        photo.season = None
    elif facet_key == "campus":
        photo.campus = None
    elif facet_key == "photo_type":
        photo.category = None


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
        if not classification.facet.is_active or not classification.node.is_active:
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
