"""
Dry-run/apply helper for mapping old taxonomy values to the 2026 scheme.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.taxonomy import TaxonomyFacet, TaxonomyNode
from app.services.taxonomy import DEFAULT_TAXONOMY, ensure_default_taxonomy, resolve_taxonomy_node, set_photo_classification

PHOTO_TYPE_MAP = {
    "Landscape": "风光类",
    "风光": "风光类",
    "Documentary": "纪实类",
    "纪实": "纪实类",
    "Activity": "纪实类",
    "活动": "纪实类",
}

YEAR_MAP = {
    str(year): f"{year}年第{label}届获奖作品"
    for year, label in [
        (2018, "一"), (2019, "二"), (2020, "三"), (2021, "四"),
        (2022, "五"), (2023, "六"), (2024, "七"), (2025, "八"),
    ]
}


async def main(apply: bool) -> None:
    report: dict[str, int] = defaultdict(int)
    unresolved: list[str] = []
    inactive_nodes: list[str] = []
    active_mismatches: list[str] = []
    async with AsyncSessionLocal() as db:
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
            active_names = [node.name for node in nodes if node.is_active]
            expected_names = list(facet_seed.get("nodes", []))
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
    asyncio.run(main(apply=args.apply))
