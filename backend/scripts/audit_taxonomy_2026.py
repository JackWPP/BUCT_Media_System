"""
Read-only audit for the 2026 taxonomy unification.

The script never writes taxonomy data. It only reads the current database and
prints a Markdown report that can be reviewed before any migration apply step.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.tag import PhotoTag, Tag
from app.models.taxonomy import PhotoClassification, TaxonomyAlias, TaxonomyFacet, TaxonomyNode

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORE_FACETS = ("gallery_series", "campus", "photo_type")
REQUIRED_TABLES = {
    "photos",
    "tags",
    "photo_tags",
    "taxonomy_facets",
    "taxonomy_nodes",
    "taxonomy_aliases",
    "photo_classifications",
}
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
LEGACY_SEASON_VALUES = {"Spring", "Summer", "Autumn", "Winter", "春季", "夏季", "秋季", "冬季"}
PORTRAIT_VALUES = {"Portrait", "人像", "人像类"}
LANDMARK_SKIP_NODE_NAMES = {"朝阳校区", "昌平校区", "海淀校区", "其它"}
SAMPLE_LIMIT = 20


def _display(value: object) -> str:
    if value is None or value == "":
        return "<EMPTY>"
    return str(value)


def _pct(count: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{count / total * 100:.1f}%"


def _counter_lines(counter: Counter[str], total: int, limit: int | None = None) -> list[str]:
    rows = counter.most_common(limit)
    if not rows:
        return ["- none"]
    return [f"- `{name}`: {count} ({_pct(count, total)})" for name, count in rows]


def _sample_line(photo_id: str, filename: str | None, detail: str) -> str:
    name = filename or "<no filename>"
    return f"{photo_id} | {name} | {detail}"


def _append_sample(samples: dict[str, list[str]], key: str, value: str) -> None:
    if len(samples[key]) < SAMPLE_LIMIT:
        samples[key].append(value)


def _write_lines(lines: Iterable[str], output: str | None) -> None:
    content = "\n".join(lines) + "\n"
    if output:
        Path(output).write_text(content, encoding="utf-8")
    print(content, end="")


async def main(include_deleted: bool, output: str | None) -> None:
    lines: list[str] = []
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    async with AsyncSessionLocal() as db:
        connection = await db.connection()
        if connection.dialect.name == "postgresql":
            await db.execute(text("SET TRANSACTION READ ONLY"))

        existing_tables = set(await connection.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
        missing_tables = sorted(REQUIRED_TABLES - existing_tables)
        if missing_tables:
            lines.extend(
                [
                    "# Taxonomy Audit 2026",
                    "",
                    f"- generated_at: {generated_at}",
                    "- mode: read-only",
                    f"- missing_tables: {', '.join(missing_tables)}",
                    "",
                    "Configure DATABASE_URL for an initialized backend database before running this audit.",
                ]
            )
            await db.rollback()
            _write_lines(lines, output)
            return

        photo_query = select(
            Photo.id,
            Photo.filename,
            Photo.status,
            Photo.season,
            Photo.category,
            Photo.campus,
            Photo.description,
        ).order_by(Photo.created_at.asc(), Photo.id.asc())
        if not include_deleted:
            photo_query = photo_query.where(Photo.status != "deleted")
        photos = list((await db.execute(photo_query)).all())
        photo_ids = {row.id for row in photos}
        photo_meta = {row.id: row for row in photos}

        facets = list(
            (
                await db.execute(
                    select(
                        TaxonomyFacet.id,
                        TaxonomyFacet.key,
                        TaxonomyFacet.name,
                        TaxonomyFacet.selection_mode,
                        TaxonomyFacet.is_active,
                    )
                )
            ).all()
        )
        facets_by_id = {facet.id: facet for facet in facets}
        facets_by_key = {facet.key: facet for facet in facets}

        nodes = list(
            (
                await db.execute(
                    select(
                        TaxonomyNode.id,
                        TaxonomyNode.facet_id,
                        TaxonomyNode.name,
                        TaxonomyNode.is_active,
                    )
                )
            ).all()
        )
        node_by_id = {node.id: node for node in nodes}
        active_nodes_by_facet: dict[str, set[str]] = defaultdict(set)
        active_taxonomy_names: set[str] = set()
        for node in nodes:
            facet = facets_by_id.get(node.facet_id)
            if facet and facet.is_active and node.is_active:
                active_nodes_by_facet[facet.key].add(node.name)
                active_taxonomy_names.add(node.name)

        aliases = list(
            (
                await db.execute(
                    select(TaxonomyAlias.alias, TaxonomyNode.name, TaxonomyFacet.key)
                    .join(TaxonomyNode, TaxonomyNode.id == TaxonomyAlias.node_id)
                    .join(TaxonomyFacet, TaxonomyFacet.id == TaxonomyNode.facet_id)
                    .where(TaxonomyNode.is_active.is_(True), TaxonomyFacet.is_active.is_(True))
                )
            ).all()
        )
        active_aliases = {row.alias: (row.key, row.name) for row in aliases}

        classification_rows = list(
            (
                await db.execute(
                    select(
                        PhotoClassification.photo_id,
                        PhotoClassification.facet_id,
                        PhotoClassification.node_id,
                    ).order_by(PhotoClassification.photo_id.asc(), PhotoClassification.facet_id.asc())
                )
            ).all()
        )
        classifications_by_photo: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        classifications_by_facet: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for row in classification_rows:
            if row.photo_id not in photo_ids:
                continue
            facet = facets_by_id.get(row.facet_id)
            node = node_by_id.get(row.node_id)
            if facet is None or node is None:
                continue
            classifications_by_photo[row.photo_id][facet.key].append(node.name)
            classifications_by_facet[facet.key].append((row.photo_id, node.name))

        tag_rows = list(
            (
                await db.execute(
                    select(Tag.id, Tag.name, Tag.usage_count, func.count(PhotoTag.photo_id).label("photo_count"))
                    .outerjoin(PhotoTag, PhotoTag.tag_id == Tag.id)
                    .group_by(Tag.id)
                    .order_by(func.count(PhotoTag.photo_id).desc(), Tag.name.asc())
                )
            ).all()
        )

        await db.rollback()

    total_photos = len(photos)
    lines.extend(
        [
            "# Taxonomy Audit 2026",
            "",
            f"- generated_at: {generated_at}",
            "- mode: read-only",
            f"- photo_scope: {'including deleted' if include_deleted else 'excluding deleted'}",
            f"- photos: {total_photos}",
            f"- facets: {len(facets)}",
            f"- active_taxonomy_nodes: {len(active_taxonomy_names)}",
            "",
        ]
    )

    lines.extend(["## Core Classification Missing", ""])
    missing_samples: dict[str, list[str]] = defaultdict(list)
    missing_counts: Counter[str] = Counter()
    for photo in photos:
        assigned = classifications_by_photo.get(photo.id, {})
        for facet_key in CORE_FACETS:
            if facet_key not in facets_by_key:
                missing_counts[f"{facet_key} facet missing"] += 1
                _append_sample(missing_samples, f"{facet_key} facet missing", _sample_line(photo.id, photo.filename, "facet missing"))
            elif not assigned.get(facet_key):
                missing_counts[f"missing {facet_key}"] += 1
                _append_sample(missing_samples, f"missing {facet_key}", _sample_line(photo.id, photo.filename, "no classification"))

        gallery_series = set(assigned.get("gallery_series", []))
        if "昌平校区摄影大赛" in gallery_series and not assigned.get("gallery_year"):
            missing_counts["competition missing gallery_year"] += 1
            _append_sample(missing_samples, "competition missing gallery_year", _sample_line(photo.id, photo.filename, "gallery_series=昌平校区摄影大赛"))
        if "投稿作品" in gallery_series and not assigned.get("source_type"):
            missing_counts["submission missing source_type"] += 1
            _append_sample(missing_samples, "submission missing source_type", _sample_line(photo.id, photo.filename, "gallery_series=投稿作品"))

    if not missing_counts:
        lines.append("- none")
    else:
        for key, count in missing_counts.most_common():
            lines.append(f"- {key}: {count} ({_pct(count, total_photos)})")
            for sample in missing_samples.get(key, []):
                lines.append(f"  - {sample}")
    lines.append("")

    lines.extend(["## Legacy Field Distribution", ""])
    for field_name in ("season", "category", "campus"):
        counter = Counter(_display(getattr(photo, field_name)) for photo in photos)
        lines.append(f"### photos.{field_name}")
        lines.extend(_counter_lines(counter, total_photos))
        lines.append("")

    lines.extend(["## Landmark Distribution", ""])
    landmark_facet = facets_by_key.get("landmark")
    if landmark_facet is None:
        lines.append("- legacy landmark facet: missing")
    else:
        lines.append(f"- legacy landmark facet active: {landmark_facet.is_active}")
        landmark_counter = Counter(name for _, name in classifications_by_facet.get("landmark", []))
        lines.extend(_counter_lines(landmark_counter, sum(landmark_counter.values())))
        building_names = active_nodes_by_facet.get("building", set())
        landscape_names = active_nodes_by_facet.get("landscape", set())
        buckets: Counter[str] = Counter()
        bucket_samples: dict[str, list[str]] = defaultdict(list)
        for photo_id, node_name in classifications_by_facet.get("landmark", []):
            if node_name in LANDMARK_SKIP_NODE_NAMES:
                bucket = "skipped_non_content"
            elif node_name in building_names:
                bucket = "mappable_to_building"
            elif node_name in landscape_names:
                bucket = "mappable_to_landscape"
            else:
                bucket = "unresolved_landmark"
            buckets[bucket] += 1
            photo = photo_meta.get(photo_id)
            _append_sample(bucket_samples, bucket, _sample_line(photo_id, getattr(photo, "filename", None), node_name))
        lines.append("")
        lines.append("### Landmark Mappability")
        if not buckets:
            lines.append("- none")
        else:
            for key, count in buckets.most_common():
                lines.append(f"- {key}: {count}")
                for sample in bucket_samples.get(key, []):
                    lines.append(f"  - {sample}")
    lines.append("")

    lines.extend(["## Unmappable Legacy Items", ""])
    unmappable_counts: Counter[str] = Counter()
    unmappable_samples: dict[str, list[str]] = defaultdict(list)
    campus_names = active_nodes_by_facet.get("campus", set())
    for photo in photos:
        if photo.category and photo.category not in PHOTO_TYPE_MAP and photo.category not in PORTRAIT_VALUES:
            key = f"category `{photo.category}`"
            unmappable_counts[key] += 1
            _append_sample(unmappable_samples, key, _sample_line(photo.id, photo.filename, "photos.category"))
        if photo.season and photo.season not in LEGACY_SEASON_VALUES:
            key = f"season `{photo.season}`"
            unmappable_counts[key] += 1
            _append_sample(unmappable_samples, key, _sample_line(photo.id, photo.filename, "photos.season"))
        if photo.campus and campus_names and photo.campus not in campus_names:
            key = f"campus `{photo.campus}`"
            unmappable_counts[key] += 1
            _append_sample(unmappable_samples, key, _sample_line(photo.id, photo.filename, "photos.campus"))
    for photo_id, node_name in classifications_by_facet.get("landmark", []):
        if node_name not in LANDMARK_SKIP_NODE_NAMES and node_name not in active_nodes_by_facet.get("building", set()) and node_name not in active_nodes_by_facet.get("landscape", set()):
            key = f"landmark `{node_name}`"
            unmappable_counts[key] += 1
            photo = photo_meta.get(photo_id)
            _append_sample(unmappable_samples, key, _sample_line(photo_id, getattr(photo, "filename", None), "legacy landmark"))
    if not unmappable_counts:
        lines.append("- none")
    else:
        for key, count in unmappable_counts.most_common():
            lines.append(f"- {key}: {count}")
            for sample in unmappable_samples.get(key, []):
                lines.append(f"  - {sample}")
    lines.append("")

    lines.extend(["## Free Tags Matching Taxonomy", ""])
    tag_exact_node = []
    tag_exact_alias = []
    for row in tag_rows:
        if row.name in active_taxonomy_names:
            tag_exact_node.append(row)
        if row.name in active_aliases:
            tag_exact_alias.append(row)
    lines.append("### Exact Node Name Matches")
    if not tag_exact_node:
        lines.append("- none")
    else:
        for row in tag_exact_node[:50]:
            lines.append(f"- `{row.name}`: usage_count={row.usage_count}, photo_count={row.photo_count}")
    lines.append("")
    lines.append("### Exact Alias Matches")
    if not tag_exact_alias:
        lines.append("- none")
    else:
        for row in tag_exact_alias[:50]:
            facet_key, node_name = active_aliases[row.name]
            lines.append(
                f"- `{row.name}` -> {facet_key}/{node_name}: usage_count={row.usage_count}, photo_count={row.photo_count}"
            )
    lines.append("")

    lines.extend(["## Single Facet Multi-Value Conflicts", ""])
    conflict_counts: Counter[str] = Counter()
    conflict_samples: dict[str, list[str]] = defaultdict(list)
    for photo_id, by_facet in classifications_by_photo.items():
        for facet_key, node_names in by_facet.items():
            facet = facets_by_key.get(facet_key)
            if facet is None or facet.selection_mode == "multiple":
                continue
            unique_names = sorted(set(node_names))
            if len(unique_names) > 1:
                conflict_counts[facet_key] += 1
                photo = photo_meta.get(photo_id)
                _append_sample(
                    conflict_samples,
                    facet_key,
                    _sample_line(photo_id, getattr(photo, "filename", None), ", ".join(unique_names)),
                )
    if not conflict_counts:
        lines.append("- none")
    else:
        for key, count in conflict_counts.most_common():
            lines.append(f"- {key}: {count} photos")
            for sample in conflict_samples.get(key, []):
                lines.append(f"  - {sample}")
    lines.append("")

    lines.extend(["## Portrait Retained Items", ""])
    portrait_counts: Counter[str] = Counter()
    portrait_samples: dict[str, list[str]] = defaultdict(list)
    for photo in photos:
        if photo.category in PORTRAIT_VALUES:
            key = f"photos.category `{photo.category}`"
            portrait_counts[key] += 1
            _append_sample(portrait_samples, key, _sample_line(photo.id, photo.filename, "legacy category retained"))
    for photo_id, by_facet in classifications_by_photo.items():
        for facet_key, node_names in by_facet.items():
            for node_name in node_names:
                if node_name in PORTRAIT_VALUES:
                    key = f"taxonomy {facet_key}/`{node_name}`"
                    portrait_counts[key] += 1
                    photo = photo_meta.get(photo_id)
                    _append_sample(portrait_samples, key, _sample_line(photo_id, getattr(photo, "filename", None), "taxonomy retained"))
    for row in tag_rows:
        if row.name in PORTRAIT_VALUES:
            key = f"free tag `{row.name}`"
            portrait_counts[key] += int(row.photo_count or row.usage_count or 0)
            _append_sample(portrait_samples, key, f"tag_id={row.id} usage_count={row.usage_count} photo_count={row.photo_count}")
    if not portrait_counts:
        lines.append("- none")
    else:
        lines.append("- note: Portrait/person entries are reported for manual retention review and are not auto-mapped.")
        for key, count in portrait_counts.most_common():
            lines.append(f"- {key}: {count}")
            for sample in portrait_samples.get(key, []):
                lines.append(f"  - {sample}")
    lines.append("")

    _write_lines(lines, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read-only audit for the 2026 taxonomy unification")
    parser.add_argument("--dry-run", action="store_true", help="No-op; audits are always read-only")
    parser.add_argument("--include-deleted", action="store_true", help="Include photos with status=deleted")
    parser.add_argument("--output", help="Optional Markdown report output path")
    args = parser.parse_args()
    try:
        asyncio.run(main(include_deleted=args.include_deleted, output=args.output))
    except SQLAlchemyError as exc:
        print("# Taxonomy Audit 2026")
        print("")
        print("- mode: read-only")
        print(f"- database error: {exc}")
