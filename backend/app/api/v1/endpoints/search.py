"""
Search API endpoint — hybrid vector + structured search.

GET /api/v1/search?q=xxx&limit=20&season=秋季&campus=昌平校区

Public endpoint (no authentication required).
"""
from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.vector_search_service import get_vector_search_service

router = APIRouter()


# ---- Response schema ----

class SearchPhotoResult(BaseModel):
    """Single photo search result."""
    photo_id: str = Field(..., description="Photo UUID")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    tags: list[str] = Field(default_factory=list, description="Associated tag names")
    classifications: dict[str, str] = Field(
        default_factory=dict,
        description="Taxonomy classifications {facet_key: node_name}",
    )


class SearchResponse(BaseModel):
    """Search API response."""
    results: list[SearchPhotoResult] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Number of results returned")
    query_time_ms: float = Field(..., ge=0, description="Query execution time in milliseconds")


# ---- Endpoint ----

@router.get("/search", response_model=SearchResponse, summary="Hybrid photo search")
async def search_photos(
    q: str = Query(..., min_length=1, max_length=500, description="Search query text"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    season: Optional[str] = Query(None, description="季节 filter (e.g. 秋季)"),
    campus: Optional[str] = Query(None, description="校区 filter (e.g. 昌平校区)"),
    category: Optional[str] = Query(None, description="Category filter (e.g. landscape)"),
    landmark: Optional[str] = Query(None, description="地标 filter"),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search photos using natural language + optional structured filters.

    The search combines:
    - **Vector similarity**: semantic matching of query text against photo embeddings
    - **Structured filters**: exact matching on season, campus, category, landmark

    Returns approved photos only, sorted by relevance score (descending).
    """
    start = time.monotonic()

    # Build filter dict from non-null query params
    filters: dict[str, str] = {}
    if season:
        filters["season"] = season
    if campus:
        filters["campus"] = campus
    if category:
        filters["category"] = category
    if landmark:
        filters["landmark"] = landmark

    service = get_vector_search_service()
    results = await service.search(
        db=db,
        query_text=q,
        filters=filters or None,
        limit=limit,
    )

    elapsed_ms = (time.monotonic() - start) * 1000

    return SearchResponse(
        results=[
            SearchPhotoResult(
                photo_id=r.photo_id,
                score=round(r.score, 4),
                tags=r.tags,
                classifications=r.classifications,
            )
            for r in results
        ],
        total=len(results),
        query_time_ms=round(elapsed_ms, 2),
    )
