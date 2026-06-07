#!/usr/bin/env python3
"""
Build or inspect the photo-level Milvus vector index.

Default mode is non-destructive: report entity counts and preview embedding
texts. Use --build to create/update the configured v2 collection. The legacy
photo_vectors collection is never dropped by this script.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.tag import PhotoTag
from app.models.taxonomy import PhotoClassification, TaxonomyNode
from app.services.embedding_service import EmbeddingService
from app.services.milvus_client import MilvusSearchClient


def _compact(parts: Iterable[str | None]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for part in parts:
        value = (part or "").strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
    return cleaned


def build_embedding_text(photo: Photo) -> tuple[str, str]:
    """Compose the canonical photo-level embedding text."""
    free_tags = [photo_tag.tag.name for photo_tag in photo.tags if photo_tag.tag]

    taxonomy_parts: list[str] = []
    priority_parts: list[str] = []
    for classification in photo.classifications:
        if not classification.facet or not classification.node:
            continue
        node = classification.node
        aliases = [alias.alias for alias in node.aliases]
        taxonomy_parts.extend([classification.facet.name, node.name, *aliases])
        if classification.facet.key in {"gallery_series", "gallery_year", "award_level", "source_type"}:
            priority_parts.extend([classification.facet.name, node.name, *aliases])

    text_parts = _compact(
        [
            photo.filename,
            photo.description,
            *free_tags,
            *taxonomy_parts,
            photo.category,
            photo.season,
            photo.campus,
            *priority_parts,
        ]
    )
    source_fields = _compact(
        [
            "filename" if photo.filename else None,
            "description" if photo.description else None,
            "free_tags" if free_tags else None,
            "taxonomy" if taxonomy_parts else None,
            "legacy_fields" if any([photo.category, photo.season, photo.campus]) else None,
        ]
    )
    return " | ".join(text_parts)[:4096], ",".join(source_fields)


async def load_photos(status: str, max_photos: int | None) -> list[Photo]:
    stmt = (
        select(Photo)
        .where(Photo.status == status)
        .options(
            selectinload(Photo.tags).selectinload(PhotoTag.tag),
            selectinload(Photo.classifications).selectinload(PhotoClassification.facet),
            selectinload(Photo.classifications)
            .selectinload(PhotoClassification.node)
            .selectinload(TaxonomyNode.aliases),
        )
        .order_by(Photo.created_at.asc())
    )
    if max_photos:
        stmt = stmt.limit(max_photos)

    async with AsyncSessionLocal() as db:
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())


async def report_collection(client: MilvusSearchClient, label: str) -> None:
    count = await client.get_entity_count()
    if count is None:
        print(f"{label}: unavailable")
    else:
        print(f"{label}: {count} entities")


async def build_index(args: argparse.Namespace, client: MilvusSearchClient) -> None:
    if not client.setup_collection():
        print("Failed to create/load Milvus collection.")
        return

    photos = await load_photos(args.status, args.max_photos)
    print(f"Photos selected: {len(photos)} (status={args.status})")
    if not photos:
        return

    embedding = EmbeddingService()
    total = 0
    for start in range(0, len(photos), args.batch_size):
        batch = photos[start : start + args.batch_size]
        payloads = [build_embedding_text(photo) for photo in batch]
        texts = [text for text, _source_fields in payloads]
        vectors = embedding.encode_batch(texts)
        if vectors is None:
            print("Embedding model unavailable; build stopped.")
            return

        for photo, vector, (embedding_text, source_fields) in zip(batch, vectors, payloads):
            await client.delete_by_photo(photo.id)
            ok = await client.insert_vectors(
                photo.id,
                [
                    {
                        "vector": vector,
                        "embedding_text": embedding_text,
                        "source_fields": source_fields,
                    }
                ],
            )
            if ok:
                total += 1
        print(f"Indexed {total}/{len(photos)}", end="\r", flush=True)

    print(f"\nBuild complete: {total} photo vectors written.")


async def run_sample_query(args: argparse.Namespace, client: MilvusSearchClient) -> None:
    if not args.query:
        return

    embedding = EmbeddingService()
    vector = embedding.encode_text(args.query)
    if vector is None:
        print("Sample query skipped: embedding model unavailable.")
        return

    hits = await client.search_vectors(vector, limit=args.query_limit)
    print(f"Sample query: {args.query}")
    if not hits:
        print("  No vector hits.")
        return

    for hit in hits:
        preview = (hit.get("embedding_text") or "").replace("\n", " ")[:120]
        print(f"  {hit.get('photo_id')} score={hit.get('score'):.4f} text={preview}")


async def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Build/report the photo-level Milvus vector index.")
    parser.add_argument("--collection", default=settings.MILVUS_COLLECTION_NAME)
    parser.add_argument("--status", default="approved", help="Photo status to index")
    parser.add_argument("--max-photos", type=int, default=None, help="Optional cap for previews/builds")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--dry-run", action="store_true", help="Preview records without writing")
    parser.add_argument("--build", action="store_true", help="Create/update the configured v2 collection")
    parser.add_argument("--query", default=None, help="Run a sample vector query after report/build")
    parser.add_argument("--query-limit", type=int, default=5)
    args = parser.parse_args()

    client = MilvusSearchClient(collection_name=args.collection)
    legacy_client = MilvusSearchClient(collection_name=settings.MILVUS_LEGACY_COLLECTION_NAME)

    print(f"Configured v2 collection: {args.collection}")
    await report_collection(client, "v2 collection")
    await report_collection(legacy_client, f"legacy collection ({settings.MILVUS_LEGACY_COLLECTION_NAME})")

    if args.build:
        await build_index(args, client)
        await report_collection(client, "v2 collection after build")
    else:
        photos = await load_photos(args.status, args.max_photos or 5)
        print(f"Dry-run preview: {len(photos)} photos")
        for photo in photos[:5]:
            embedding_text, source_fields = build_embedding_text(photo)
            print(f"  {photo.id} fields={source_fields} text={embedding_text[:180]}")

    await run_sample_query(args, client)


if __name__ == "__main__":
    asyncio.run(main())
