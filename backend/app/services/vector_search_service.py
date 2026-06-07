"""
Hybrid vector + structured search service.

Workflow:
1. Encode user query to a vector.
2. Search Milvus for semantically similar photo-level embeddings.
3. Load approved photos and apply structured taxonomy/photo filters.
4. Fall back to keyword/taxonomy search when vector search is unavailable.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.photo import Photo
from app.models.tag import Tag, PhotoTag
from app.models.taxonomy import PhotoClassification, TaxonomyAlias, TaxonomyFacet, TaxonomyNode
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


@dataclass
class SearchOutcome:
    """Search result list plus the mode actually used."""

    results: list[SearchResult] = field(default_factory=list)
    search_mode: str = "keyword"
    fallback_reason: Optional[str] = None
    index_version: Optional[str] = None


class VectorSearchService:
    """High-level search: photo-level vector first, keyword/taxonomy fallback."""

    def __init__(self) -> None:
        self._embedding = get_embedding_service()
        self._milvus = get_milvus_client()

    async def search(
        self,
        db: AsyncSession,
        query_text: str,
        filters: Optional[dict[str, str]] = None,
        limit: int = 20,
    ) -> SearchOutcome:
        """Search photos by natural language query.

        1. Try photo-level semantic search via Milvus.
        2. Apply structured taxonomy/photo filters.
        3. Fall back to keyword/taxonomy search if vector search is unavailable
           or yields no usable approved photo candidates.
        """
        fallback_reason: Optional[str] = None

        try:
            query_vector = self._embedding.encode_text(query_text)
        except Exception as exc:
            logger.warning("VectorSearchService: embedding failed, using keyword fallback — %s", exc)
            query_vector = None
            fallback_reason = "embedding_failed"

        if query_vector is None:
            if fallback_reason is None:
                logger.warning("VectorSearchService: embedding unavailable, using keyword fallback")
                fallback_reason = "embedding_unavailable"
            return await self._keyword_fallback(db, query_text, filters, limit, fallback_reason)

        try:
            vector_hits = await self._milvus.search_vectors(
                query_vector=query_vector,
                limit=max(limit * 5, 20),
            )
        except Exception as exc:
            logger.warning("VectorSearchService: Milvus search failed, using keyword fallback — %s", exc)
            return await self._keyword_fallback(db, query_text, filters, limit, "milvus_failed")

        if vector_hits:
            vector_results = await self._results_from_vector_hits(db, vector_hits, filters, limit)
            if vector_results:
                return SearchOutcome(
                    results=vector_results,
                    search_mode="hybrid" if filters else "vector",
                    index_version=self._milvus.collection_name,
                )
            fallback_reason = "vector_candidates_unusable"
        else:
            fallback_reason = "vector_no_hits"

        return await self._keyword_fallback(db, query_text, filters, limit, fallback_reason)

    async def _results_from_vector_hits(
        self,
        db: AsyncSession,
        hits: list[dict[str, Any]],
        filters: Optional[dict[str, str]],
        limit: int,
    ) -> list[SearchResult]:
        scored_ids: dict[str, float] = {}
        ordered_ids: list[str] = []
        for hit in hits:
            photo_id = str(hit.get("photo_id") or "")
            if not photo_id or photo_id.startswith("tag_"):
                continue
            if photo_id not in scored_ids:
                ordered_ids.append(photo_id)
            scored_ids[photo_id] = max(scored_ids.get(photo_id, 0.0), float(hit.get("score") or 0.0))

        if not ordered_ids:
            return []

        stmt = (
            select(Photo)
            .where(Photo.id.in_(ordered_ids), Photo.status == "approved")
            .options(*self._photo_options())
        )
        result = await db.execute(stmt)
        photos = {photo.id: photo for photo in result.scalars().all()}

        results: list[SearchResult] = []
        for photo_id in ordered_ids:
            photo = photos.get(photo_id)
            if photo is None or not self._photo_matches_filters(photo, filters):
                continue
            results.append(self._to_result(photo, self._normalize_vector_score(scored_ids[photo_id])))
            if len(results) >= limit:
                break
        return results

    async def _keyword_fallback(
        self,
        db: AsyncSession,
        query_text: str,
        filters: Optional[dict[str, str]],
        limit: int,
        reason: Optional[str],
    ) -> SearchOutcome:
        terms = self._query_terms(query_text)
        conditions = [self._keyword_condition(term) for term in terms]
        conditions = [condition for condition in conditions if condition is not None]

        stmt = (
            select(Photo)
            .where(Photo.status == "approved")
            .options(*self._photo_options())
            .limit(max(limit * 5, 50))
        )
        if conditions:
            stmt = stmt.where(or_(*conditions))
        for condition in self._structured_filter_conditions(filters):
            stmt = stmt.where(condition)
        stmt = stmt.order_by(Photo.published_at.desc().nullslast(), Photo.created_at.desc())

        result = await db.execute(stmt)
        photos = list(result.scalars().unique().all())
        scored = [
            (photo, self._score_keyword_photo(photo, terms))
            for photo in photos
            if self._photo_matches_filters(photo, filters)
        ]
        scored.sort(key=lambda item: (-item[1], -self._created_timestamp(item[0])))

        return SearchOutcome(
            results=[self._to_result(photo, score) for photo, score in scored[:limit]],
            search_mode="keyword",
            fallback_reason=reason,
            index_version=self._milvus.collection_name,
        )

    @staticmethod
    def _photo_options():
        return (
            selectinload(Photo.tags).selectinload(PhotoTag.tag),
            selectinload(Photo.classifications).selectinload(PhotoClassification.facet),
            selectinload(Photo.classifications)
            .selectinload(PhotoClassification.node)
            .selectinload(TaxonomyNode.aliases),
        )

    @staticmethod
    def _query_terms(query_text: str) -> list[str]:
        raw_terms = [query_text.strip()]
        raw_terms.extend(re.split(r"[\s,，、;；]+", query_text.strip()))
        terms: list[str] = []
        seen: set[str] = set()
        for term in raw_terms:
            normalized = term.strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key not in seen:
                seen.add(key)
                terms.append(normalized)
        return terms

    @staticmethod
    def _keyword_condition(term: str):
        pattern = f"%{term}%"
        tag_subquery = (
            select(PhotoTag.photo_id)
            .join(Tag, Tag.id == PhotoTag.tag_id)
            .where(Tag.name.ilike(pattern))
        )
        taxonomy_node_subquery = (
            select(PhotoClassification.photo_id)
            .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
            .join(TaxonomyFacet, TaxonomyFacet.id == PhotoClassification.facet_id)
            .where(
                TaxonomyFacet.is_active.is_(True),
                TaxonomyNode.is_active.is_(True),
                TaxonomyNode.is_selectable.is_(True),
                TaxonomyNode.name.ilike(pattern),
            )
        )
        taxonomy_alias_subquery = (
            select(PhotoClassification.photo_id)
            .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
            .join(TaxonomyFacet, TaxonomyFacet.id == PhotoClassification.facet_id)
            .join(TaxonomyAlias, TaxonomyAlias.node_id == TaxonomyNode.id)
            .where(
                TaxonomyFacet.is_active.is_(True),
                TaxonomyNode.is_active.is_(True),
                TaxonomyNode.is_selectable.is_(True),
                TaxonomyAlias.alias.ilike(pattern),
            )
        )
        return or_(
            Photo.filename.ilike(pattern),
            Photo.description.ilike(pattern),
            Photo.id.in_(tag_subquery),
            Photo.id.in_(taxonomy_node_subquery),
            Photo.id.in_(taxonomy_alias_subquery),
        )

    @staticmethod
    def _structured_filter_conditions(filters: Optional[dict[str, str]]) -> list[Any]:
        if not filters:
            return []

        conditions: list[Any] = []
        photo_columns = set(Photo.__table__.columns.keys())
        for key, value in filters.items():
            if not value:
                continue
            normalized_key = str(value).lower().replace(" ", "-")
            facet_keys = ("building", "landscape") if key == "landmark" else (key,)
            taxonomy_subquery = (
                select(PhotoClassification.photo_id)
                .join(TaxonomyFacet, TaxonomyFacet.id == PhotoClassification.facet_id)
                .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
                .outerjoin(TaxonomyAlias, TaxonomyAlias.node_id == TaxonomyNode.id)
                .where(
                    TaxonomyFacet.key.in_(facet_keys),
                    TaxonomyFacet.is_active.is_(True),
                    TaxonomyNode.is_active.is_(True),
                    TaxonomyNode.is_selectable.is_(True),
                    or_(
                        TaxonomyNode.name == value,
                        TaxonomyNode.key == normalized_key,
                        TaxonomyAlias.alias == value,
                    ),
                )
            )
            condition = Photo.id.in_(taxonomy_subquery)
            if key in photo_columns:
                condition = or_(condition, getattr(Photo, key) == value)
            conditions.append(condition)
        return conditions

    @staticmethod
    def _photo_matches_filters(photo: Photo, filters: Optional[dict[str, str]]) -> bool:
        if not filters:
            return True

        taxonomy_values: dict[str, set[str]] = {}
        for classification in photo.classifications:
            if not classification.facet or not classification.node:
                continue
            if not classification.facet.is_active or not classification.node.is_active or not classification.node.is_selectable:
                continue
            values = taxonomy_values.setdefault(classification.facet.key, set())
            values.add(classification.node.name)
            values.add(classification.node.key)
            for alias in classification.node.aliases:
                values.add(alias.alias)

        for key, value in filters.items():
            if not value:
                continue
            expected = str(value)
            photo_value = getattr(photo, key, None)
            if key == "landmark":
                taxonomy_match = expected in (
                    taxonomy_values.get("building", set()) | taxonomy_values.get("landscape", set())
                )
            else:
                taxonomy_match = expected in taxonomy_values.get(key, set())
            photo_match = photo_value is not None and str(photo_value) == expected
            if not taxonomy_match and not photo_match:
                return False
        return True

    @staticmethod
    def _normalize_vector_score(score: float) -> float:
        if 0.0 <= score <= 1.0:
            return round(score, 4)
        if -1.0 <= score < 0.0:
            return round((score + 1.0) / 2.0, 4)
        return round(max(0.0, min(score, 1.0)), 4)

    @staticmethod
    def _created_timestamp(photo: Photo) -> float:
        return photo.created_at.timestamp() if photo.created_at else 0.0

    @staticmethod
    def _score_keyword_photo(photo: Photo, terms: list[str]) -> float:
        if not terms:
            return 0.0

        score = 0.0
        filename = (photo.filename or "").casefold()
        description = (photo.description or "").casefold()
        tag_names = [(photo_tag.tag.name or "").casefold() for photo_tag in photo.tags if photo_tag.tag]
        taxonomy_names: list[str] = []
        for classification in photo.classifications:
            if classification.node:
                taxonomy_names.append((classification.node.name or "").casefold())
                taxonomy_names.extend((alias.alias or "").casefold() for alias in classification.node.aliases)

        for term in terms:
            term_key = term.casefold()
            if term_key in filename:
                score += 1.0
            if term_key in description:
                score += 0.8
            if any(term_key in tag for tag in tag_names):
                score += 0.7
            if any(term_key in name for name in taxonomy_names):
                score += 0.9

        return round(min(score / max(len(terms), 1), 1.0), 4)

    @staticmethod
    def _to_result(photo: Photo, score: float) -> SearchResult:
        classifications: dict[str, str] = {}
        for classification in photo.classifications:
            if classification.facet and classification.node:
                if not classification.facet.is_active or not classification.node.is_active or not classification.node.is_selectable:
                    continue
                classifications[classification.facet.key] = classification.node.name

        return SearchResult(
            photo_id=photo.id,
            score=score,
            tags=[photo_tag.tag.name for photo_tag in photo.tags if photo_tag.tag],
            classifications=classifications,
        )


# ---- Module-level singleton ----
_service: Optional[VectorSearchService] = None


def get_vector_search_service() -> VectorSearchService:
    """Return (and lazily create) the global VectorSearchService instance."""
    global _service
    if _service is None:
        _service = VectorSearchService()
    return _service
