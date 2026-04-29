"""
Schemas for smart search interpretation.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SearchInterpretRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="User search query")


class SearchInterpretResponse(BaseModel):
    facet_filters: dict[str, str] = Field(default_factory=dict, description="Resolved facet filters")
    keywords: list[str] = Field(default_factory=list, description="Remaining keywords after facet extraction")
    original_query: str = Field(..., description="Original user query")
    method: str = Field(..., description="Interpretation method: rule | ai | fallback")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    explanation: Optional[str] = Field(None, description="Human-readable explanation of the interpretation")
