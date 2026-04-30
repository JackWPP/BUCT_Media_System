"""
Taxonomy schemas.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaxonomyFacetBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    selection_mode: str = Field(default="single", pattern="^(single|multiple)$")
    is_active: bool = True
    sort_order: int = 0


class TaxonomyFacetCreate(TaxonomyFacetBase):
    is_system: bool = False


class TaxonomyFacetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    selection_mode: Optional[str] = Field(None, pattern="^(single|multiple)$")
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class TaxonomyAliasResponse(BaseModel):
    id: int
    alias: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaxonomyNodeBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int = 0
    is_active: bool = True
    aliases: list[str] = Field(default_factory=list)


class TaxonomyNodeCreate(TaxonomyNodeBase):
    pass


class TaxonomyNodeUpdate(BaseModel):
    key: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    aliases: Optional[list[str]] = None

    model_config = ConfigDict(extra="forbid")


class TaxonomyNodeResponse(BaseModel):
    id: int
    facet_id: int
    parent_id: Optional[int]
    key: str
    name: str
    description: Optional[str]
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    aliases: list[TaxonomyAliasResponse] = Field(default_factory=list)
    children: list["TaxonomyNodeResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TaxonomyFacetResponse(BaseModel):
    id: int
    key: str
    name: str
    description: Optional[str]
    selection_mode: str
    is_system: bool
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    nodes: list[TaxonomyNodeResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TaxonomyValueResponse(BaseModel):
    facet_key: str
    facet_name: str
    node_id: int
    node_key: str
    node_name: str
    path: list[str] = Field(default_factory=list)


class PhotoClassificationUpdateSchema(BaseModel):
    """Batch update photo classifications: { facet_key: node_id }"""
    classifications: dict[str, int] = Field(
        default_factory=dict,
        description="Mapping of facet_key to node_id",
    )

    model_config = ConfigDict(extra="forbid")


TaxonomyNodeResponse.model_rebuild()
