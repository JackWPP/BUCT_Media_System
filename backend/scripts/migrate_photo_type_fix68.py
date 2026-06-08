"""
Dry-run/apply helper for Fix_68 photo_type realignment.

The new public topic facet is `建筑楼宇 / 校区设施 / 自然生态`. Old values such
as `校园风光` are only migrated when existing content facets make the target
unambiguous. Ambiguous or documentary values are left unassigned for manual
tagging tasks.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.taxonomy import PhotoClassification, TaxonomyFacet, TaxonomyNode
from app.services.taxonomy import ensure_default_taxonomy

OLD_UNRESOLVED_TYPES = {"人文纪实", "纪实", "纪实类", "活动", "人像", "Portrait"}
NEW_PHOTO_TYPES = {"建筑楼宇", "校区设施", "自然生态"}
NATURE_LANDSCAPES = {"荷塘", "柳湖", "玉屏山", "北化知行园", "静心亭（柳湖）", "师贤亭（荷塘）", "燕贺亭（玉屏山）"}


async def _facet(db, key: str) -> TaxonomyFacet | None:
    result = await db.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == key))
    return result.scalar_one_or_none()


async def _node_by_name(db, facet: TaxonomyFacet, name: str) -> TaxonomyNode:
    result = await db.execute(
        select(TaxonomyNode).where(
            TaxonomyNode.facet_id == facet.id,
            TaxonomyNode.name == name,
            TaxonomyNode.is_active.is_(True),
            TaxonomyNode.is_selectable.is_(True),
        )
    )
    node = result.scalar_one_or_none()
    if node is None:
        raise RuntimeError(f"missing active selectable photo_type node: {name}")
    return node


def _classifications_by_facet(photo: Photo) -> dict[str, set[str]]:
    values: dict[str, set[str]] = defaultdict(set)
    for classification in photo.classifications or []:
        if not classification.facet or not classification.node:
            continue
        if not classification.facet.is_active:
            continue
        values[classification.facet.key].add(classification.node.name)
    return values


def _target_for_photo(photo: Photo, values: dict[str, set[str]]) -> tuple[str | None, str]:
    current_types = values.get("photo_type", set())
    current_new_types = current_types & NEW_PHOTO_TYPES
    if len(current_new_types) == 1 and not (current_types - NEW_PHOTO_TYPES):
        current = next(iter(current_new_types))
        return current, f"already_{current}"
    if len(current_new_types) > 1:
        return None, "unresolved_conflict"
    if current_types & OLD_UNRESOLVED_TYPES or photo.category in OLD_UNRESOLVED_TYPES:
        return None, "unresolved_documentary_or_portrait"

    has_building = bool(values.get("building"))
    has_facility = bool(values.get("facility"))
    has_nature = bool(values.get("natural_phenomenon") or values.get("animal") or values.get("plant"))
    has_nature_landscape = bool(values.get("landscape", set()) & NATURE_LANDSCAPES)

    target_signals: list[str] = []
    if has_building:
        target_signals.append("建筑楼宇")
    if has_facility:
        target_signals.append("校区设施")
    if has_nature or has_nature_landscape:
        target_signals.append("自然生态")

    unique_targets = list(dict.fromkeys(target_signals))
    if len(unique_targets) == 1:
        return unique_targets[0], {
            "建筑楼宇": "mapped_to_building",
            "校区设施": "mapped_to_facility",
            "自然生态": "mapped_to_nature",
        }[unique_targets[0]]
    if len(unique_targets) > 1:
        return None, "unresolved_conflict"
    if current_types or photo.category:
        return None, "unresolved_insufficient_signals"
    return None, "unresolved_missing_source"


async def _clear_photo_type(db, photo: Photo, facet: TaxonomyFacet) -> None:
    existing = [
        classification
        for classification in photo.classifications or []
        if classification.facet_id == facet.id
    ]
    for classification in existing:
        await db.delete(classification)


async def _replace_photo_type(db, photo: Photo, facet: TaxonomyFacet, target_node: TaxonomyNode) -> None:
    existing = [
        classification
        for classification in photo.classifications or []
        if classification.facet_id == facet.id
    ]
    keep = None
    for classification in existing:
        if classification.node_id == target_node.id:
            keep = classification
            break
    if keep is None:
        keep = PhotoClassification(photo_id=photo.id, facet_id=facet.id, node_id=target_node.id)
        db.add(keep)
    for classification in existing:
        if classification is not keep:
            await db.delete(classification)


async def migrate(db, apply: bool) -> tuple[Counter[str], dict[str, list[str]]]:
    report: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)

    await ensure_default_taxonomy(db)
    photo_type_facet = await _facet(db, "photo_type")
    if photo_type_facet is None:
        raise RuntimeError("photo_type facet is missing")
    targets = {
        name: await _node_by_name(db, photo_type_facet, name)
        for name in ("建筑楼宇", "校区设施", "自然生态")
    }

    rows = await db.execute(
        select(Photo)
        .options(
            selectinload(Photo.classifications).selectinload(PhotoClassification.facet),
            selectinload(Photo.classifications).selectinload(PhotoClassification.node),
        )
        .order_by(Photo.created_at.asc())
    )
    for photo in rows.scalars().all():
        values = _classifications_by_facet(photo)
        target, bucket = _target_for_photo(photo, values)
        report[bucket] += 1
        if len(examples[bucket]) < 25:
            old_type = "、".join(sorted(values.get("photo_type", set()))) or photo.category or "none"
            examples[bucket].append(f"{photo.id}: {photo.filename} | old={old_type} | target={target or '-'}")
        if apply and target:
            await _replace_photo_type(db, photo, photo_type_facet, targets[target])
        elif apply and values.get("photo_type"):
            await _clear_photo_type(db, photo, photo_type_facet)

    return report, examples


async def main(apply: bool) -> None:
    async with AsyncSessionLocal() as db:
        report, examples = await migrate(db, apply)
        if apply:
            await db.commit()
        else:
            await db.rollback()

    print("Fix_68 photo_type migration report")
    print(f"mode: {'apply' if apply else 'dry-run'}")
    for key, count in sorted(report.items()):
        print(f"{key}: {count}")
        for example in examples.get(key, []):
            print(f"- {example}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate old photo_type classifications to Fix_68 topics")
    parser.add_argument("--apply", action="store_true", help="Write deterministic mappings")
    args = parser.parse_args()
    try:
        asyncio.run(main(apply=args.apply))
    except SQLAlchemyError as exc:
        print("Fix_68 photo_type migration report")
        print(f"mode: {'apply' if args.apply else 'dry-run'}")
        print(f"database error: {exc}")
