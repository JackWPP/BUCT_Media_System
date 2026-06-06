"""
Hybrid vector + structured search service.

Workflow:
1. Encode user query → vector (bge-small-zh-v1.5)
2. Search Milvus for semantically similar tags
3. Find photos that have those tags in PostgreSQL
4. Score photos by tag match quality
5. Apply structured filters (season, campus, etc.)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.photo import Photo
from app.models.tag import Tag, PhotoTag
from app.models.taxonomy import PhotoClassification, TaxonomyFacet, TaxonomyNode
from app.services.embedding_service import get_embedding_service
from app.services.milvus_client import get_milvus_client

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result with metadata."""
    photo_id: str
    score: float
    tags: list[str] = field(default_factory=list)
    classifications: dict[str, str] = field(default_factory=dict)


class VectorSearchService:
    """High-level hybrid search: vector tag matching + structured photo filters."""

    def __init__(self) -> None:
        self._embedding = get_embedding_service()
        self._milvus = get_milvus_client()

    async def search(
        self,
        db: AsyncSession,
        query_text: str,
        filters: Optional[dict[str, str]] = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search photos by natural language query.

        1. Find semantically similar tags via Milvus vector search
        2. Find photos that have those tags
        3. Score and rank photos
        """
        # 1. Encode query
        query_vector = self._embedding.encode_text(query_text)
        if query_vector is None:
            logger.warning("VectorSearchService: embedding unavailable")
            return []

        # 2. Search Milvus for similar tags (get more than needed for filtering)
        tag_hits = await self._milvus.search_vectors(
            query_vector=query_vector,
            limit=limit * 5,
        )

        if not tag_hits:
            return []

        # Extract tag names and scores
        tag_scores: dict[str, float] = {}
        for hit in tag_hits:
            tag_text = hit.get("tag_text", "")
            score = hit.get("score", 0.0)
            if tag_text and tag_text not in tag_scores:
                tag_scores[tag_text] = score

        if not tag_scores:
            return []

        # 3. Find photos that have these tags (ordered by match quality)
        tag_names = list(tag_scores.keys())

        # Query photos that have any of the matched tags
        # We score by summing the tag similarity scores
        photo_tag_query = (
            select(
                PhotoTag.photo_id,
                Tag.name.label("tag_name"),
            )
            .join(Tag, Tag.id == PhotoTag.tag_id)
            .where(Tag.name.in_(tag_names))
        )
        pt_result = await db.execute(photo_tag_query)
        photo_tag_rows = pt_result.fetchall()

        # Build photo → score map
        photo_scores: dict[str, float] = {}
        photo_matched_tags: dict[str, list[str]] = {}
        for photo_id, tag_name in photo_tag_rows:
            tag_score = tag_scores.get(tag_name, 0.0)
            photo_scores[photo_id] = photo_scores.get(photo_id, 0.0) + tag_score
            photo_matched_tags.setdefault(photo_id, []).append(tag_name)

        if not photo_scores:
            return []

        # Sort by score, take top candidates
        sorted_photos = sorted(photo_scores.items(), key=lambda x: -x[1])[:limit * 2]
        candidate_ids = [pid for pid, _ in sorted_photos]

        # 4. Load full photo data with tags and classifications
        stmt = (
            select(Photo)
            .where(Photo.id.in_(candidate_ids), Photo.status == "approved")
            .options(
                selectinload(Photo.tags).selectinload(PhotoTag.tag),
                selectinload(Photo.classifications).selectinload(PhotoClassification.facet),
                selectinload(Photo.classifications).selectinload(PhotoClassification.node),
            )
        )
        result = await db.execute(stmt)
        photos = {p.id: p for p in result.scalars().all()}

        # 5. Apply structured filters and build results
        results: list[SearchResult] = []
        for photo_id, raw_score in sorted_photos:
            photo = photos.get(photo_id)
            if photo is None:
                continue

            # Apply structured filters (season, campus, etc.)
            if filters:
                skip = False
                taxonomy_values: dict[str, set[str]] = {}
                for classification in photo.classifications:
                    if classification.facet and classification.node:
                        taxonomy_values.setdefault(classification.facet.key, set()).add(classification.node.name)
                for key, value in filters.items():
                    if not value:
                        continue
                    if key in taxonomy_values:
                        if str(value) not in taxonomy_values[key]:
                            skip = True
                            break
                    else:
                        photo_value = getattr(photo, key, None)
                        if photo_value is None or str(photo_value) != str(value):
                            skip = True
                            break
                if skip:
                    continue

            # Normalize score to 0-1 range
            max_possible = sum(sorted(tag_scores.values(), reverse=True)[:len(photo_matched_tags.get(photo_id, []))])
            normalized_score = raw_score / max_possible if max_possible > 0 else 0.0
            normalized_score = min(normalized_score, 1.0)

            # Collect tag names
            tag_names_list = [pt.tag.name for pt in photo.tags if pt.tag]

            # Collect classifications
            classifications: dict[str, str] = {}
            for pc in photo.classifications:
                if pc.facet and pc.node:
                    classifications[pc.facet.key] = pc.node.name

            results.append(SearchResult(
                photo_id=photo_id,
                score=round(normalized_score, 4),
                tags=tag_names_list,
                classifications=classifications,
            ))

            if len(results) >= limit:
                break

        return results


# ---- Module-level singleton ----
_service: Optional[VectorSearchService] = None


def get_vector_search_service() -> VectorSearchService:
    """Return (and lazily create) the global VectorSearchService instance."""
    global _service
    if _service is None:
        _service = VectorSearchService()
    return _service
