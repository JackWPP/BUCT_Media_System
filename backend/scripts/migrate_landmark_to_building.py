"""
Dry-run/apply helper for splitting legacy landmark classifications.

Legacy `landmark` mixed campus, buildings, scenic landmarks, and "其它".
The 2026 taxonomy uses canonical `building` for A-class buildings and
`landscape` for C-class scenic landmarks. This script reports all decisions
before any production write.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import AsyncSessionLocal
from app.models.taxonomy import PhotoClassification, TaxonomyFacet, TaxonomyNode
from app.services.taxonomy import ensure_default_taxonomy

SKIP_NODE_NAMES = {"朝阳校区", "昌平校区", "海淀校区", "其它"}


async def _facet(db, key: str) -> TaxonomyFacet | None:
    result = await db.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == key))
    return result.scalar_one_or_none()


async def _active_nodes_by_name(db, facet: TaxonomyFacet | None) -> dict[str, TaxonomyNode]:
    if facet is None:
        return {}
    result = await db.execute(
        select(TaxonomyNode).where(
            TaxonomyNode.facet_id == facet.id,
            TaxonomyNode.is_active.is_(True),
        )
    )
    return {node.name: node for node in result.scalars().all()}


async def _copy_classification(
    db,
    classification: PhotoClassification,
    target_facet: TaxonomyFacet,
    target_node: TaxonomyNode,
) -> bool:
    existing = await db.execute(
        select(PhotoClassification).where(
            PhotoClassification.photo_id == classification.photo_id,
            PhotoClassification.facet_id == target_facet.id,
            PhotoClassification.node_id == target_node.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False
    db.add(
        PhotoClassification(
            photo_id=classification.photo_id,
            facet_id=target_facet.id,
            node_id=target_node.id,
        )
    )
    return True


async def main(apply: bool) -> None:
    report: dict[str, int] = defaultdict(int)
    examples: dict[str, list[str]] = defaultdict(list)

    async with AsyncSessionLocal() as db:
        await ensure_default_taxonomy(db)

        landmark = await _facet(db, "landmark")
        building = await _facet(db, "building")
        landscape = await _facet(db, "landscape")
        building_nodes = await _active_nodes_by_name(db, building)
        landscape_nodes = await _active_nodes_by_name(db, landscape)

        if landmark is None:
            print("landmark migration report")
            print(f"mode: {'apply' if apply else 'dry-run'}")
            print("legacy landmark facet: missing")
            await db.rollback()
            return
        if building is None or landscape is None:
            raise RuntimeError("building and landscape facets must exist before migration")

        rows = await db.execute(
            select(PhotoClassification, TaxonomyNode)
            .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
            .where(PhotoClassification.facet_id == landmark.id)
            .order_by(PhotoClassification.photo_id.asc())
        )

        for classification, source_node in rows.all():
            source_name = source_node.name
            target_facet = None
            target_node = None
            bucket = "unresolved"

            if source_name in SKIP_NODE_NAMES:
                bucket = "skipped_non_content"
            elif source_name in building_nodes:
                target_facet = building
                target_node = building_nodes[source_name]
                bucket = "mapped_to_building"
            elif source_name in landscape_nodes:
                target_facet = landscape
                target_node = landscape_nodes[source_name]
                bucket = "mapped_to_landscape"

            report[bucket] += 1
            if len(examples[bucket]) < 20:
                examples[bucket].append(f"{classification.photo_id}: {source_name}")

            if apply and target_facet is not None and target_node is not None:
                if await _copy_classification(db, classification, target_facet, target_node):
                    report[f"{bucket}_created"] += 1

        if apply:
            landmark.is_active = False
            await db.commit()
        else:
            await db.rollback()

    print("landmark migration report")
    print(f"mode: {'apply' if apply else 'dry-run'}")
    for key, count in sorted(report.items()):
        print(f"{key}: {count}")
        for example in examples.get(key, []):
            print(f"- {example}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split legacy landmark classifications into building/landscape")
    parser.add_argument("--apply", action="store_true", help="Write mapped classifications and deactivate landmark facet")
    args = parser.parse_args()
    try:
        asyncio.run(main(apply=args.apply))
    except SQLAlchemyError as exc:
        print("landmark migration report")
        print(f"mode: {'apply' if args.apply else 'dry-run'}")
        print(f"database error: {exc}")
