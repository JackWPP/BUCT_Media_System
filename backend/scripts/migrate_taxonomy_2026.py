"""
Dry-run/apply helper for mapping old taxonomy values to the 2026 scheme.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.taxonomy import TaxonomyFacet, TaxonomyNode
from app.services.taxonomy import (
    DEFAULT_TAXONOMY,
    _flatten_seed_nodes,
    ensure_default_taxonomy,
    resolve_taxonomy_node,
    set_photo_classification,
)

PHOTO_TYPE_MAP = {
    "Landscape": "校园风光",
    "风光": "校园风光",
    "风光类": "校园风光",
    "Documentary": "人文纪实",
    "纪实": "人文纪实",
    "纪实类": "人文纪实",
    "Activity": "人文纪实",
    "活动": "人文纪实",
    "自然生态": "自然生态",
}

YEAR_MAP = {
    str(year): f"第{label}届获奖作品（{year}年）"
    for year, label in [
        (2018, "一"), (2019, "二"), (2020, "三"), (2021, "四"),
        (2022, "五"), (2023, "六"), (2024, "七"), (2025, "八"),
    ]
}


def _flatten_active_nodes(nodes: list[TaxonomyNode]) -> list[str]:
    by_parent: dict[int | None, list[TaxonomyNode]] = defaultdict(list)
    for node in nodes:
        if node.is_active:
            by_parent[node.parent_id].append(node)

    def visit(parent_id: int | None) -> list[str]:
        names: list[str] = []
        siblings = sorted(by_parent.get(parent_id, []), key=lambda item: (item.sort_order, item.id))
        for node in siblings:
            names.append(node.name)
            names.extend(visit(node.id))
        return names

    return visit(None)


async def main(apply: bool) -> None:
    report: dict[str, int] = defaultdict(int)
    unresolved: list[str] = []
    inactive_nodes: list[str] = []
    active_mismatches: list[str] = []
    async with AsyncSessionLocal() as db:
        required_tables = {"photos", "taxonomy_facets", "taxonomy_nodes", "photo_classifications"}
        connection = await db.connection()
        existing_tables = set(await connection.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
        missing_tables = sorted(required_tables - existing_tables)
        if missing_tables:
            print("taxonomy migration report")
            print(f"mode: {'apply' if apply else 'dry-run'}")
            print(f"missing tables: {', '.join(missing_tables)}")
            print("Configure DATABASE_URL for an initialized backend database before running this script.")
            return

        await ensure_default_taxonomy(db)
        result = await db.execute(select(Photo).order_by(Photo.created_at.asc()))
        photos = result.scalars().all()
        for photo in photos:
            if photo.category in PHOTO_TYPE_MAP:
                node = await resolve_taxonomy_node(db, "photo_type", PHOTO_TYPE_MAP[photo.category])
                if node and apply:
                    await set_photo_classification(db, photo, "photo_type", node)
                report["photo_type_mapped"] += 1
            elif photo.category == "Portrait":
                unresolved.append(f"{photo.id}: Portrait requires manual classification")

            desc = photo.description or ""
            if "摄影大赛" in desc:
                node = await resolve_taxonomy_node(db, "gallery_series", "昌平校区摄影大赛")
                if node and apply:
                    await set_photo_classification(db, photo, "gallery_series", node)
                report["gallery_series_mapped"] += 1

            for year, target in YEAR_MAP.items():
                if year in desc:
                    node = await resolve_taxonomy_node(db, "gallery_year", target)
                    if node and apply:
                        await set_photo_classification(db, photo, "gallery_year", node)
                    report["gallery_year_mapped"] += 1
                    break

        if apply:
            await db.commit()
        else:
            await db.rollback()

        await ensure_default_taxonomy(db)
        for facet_seed in DEFAULT_TAXONOMY:
            facet_result = await db.execute(
                select(TaxonomyFacet).where(TaxonomyFacet.key == facet_seed["key"])
            )
            facet = facet_result.scalar_one_or_none()
            if facet is None:
                active_mismatches.append(f"{facet_seed['key']}: missing facet")
                continue
            nodes_result = await db.execute(
                select(TaxonomyNode).where(TaxonomyNode.facet_id == facet.id)
            )
            nodes = list(nodes_result.scalars().all())
            active_names = _flatten_active_nodes(nodes)
            expected_names = _flatten_seed_nodes(facet_seed.get("nodes", []))
            if active_names != expected_names:
                active_mismatches.append(
                    f"{facet.key}: active={active_names} expected={expected_names}"
                )
            inactive_nodes.extend(
                f"{facet.key}/{node.name}"
                for node in nodes
                if not node.is_active
            )
        await db.rollback()

    print("taxonomy migration report")
    print(f"mode: {'apply' if apply else 'dry-run'}")
    for key, count in sorted(report.items()):
        print(f"{key}: {count}")
    print(f"unresolved: {len(unresolved)}")
    for item in unresolved[:50]:
        print(f"- {item}")
    print(f"inactive legacy nodes: {len(inactive_nodes)}")
    for item in inactive_nodes[:50]:
        print(f"- {item}")
    print(f"active taxonomy mismatches: {len(active_mismatches)}")
    for item in active_mismatches[:20]:
        print(f"- {item}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write mapped taxonomy values")
    args = parser.parse_args()
    try:
        asyncio.run(main(apply=args.apply))
    except SQLAlchemyError as exc:
        print("taxonomy migration report")
        print(f"mode: {'apply' if args.apply else 'dry-run'}")
        print(f"database error: {exc}")
        print("No changes were applied unless --apply reached the final commit step.")
