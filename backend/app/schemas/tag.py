"""
Tag Pydantic schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TagBase(BaseModel):
    """Base tag schema"""
    name: str = Field(..., min_length=1, max_length=100, description="Tag name")
    category: Optional[str] = Field(None, max_length=50, description="Tag category: object/scene/color/mood")
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="HEX color code")


class TagCreate(TagBase):
    """Schema for creating a tag"""
    pass


class TagUpdate(BaseModel):
    """Schema for updating a tag"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    
    model_config = ConfigDict(extra='forbid')


class TagInDB(TagBase):
    """Tag in database"""
    id: int
    usage_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TagResponse(TagInDB):
    """Tag response schema"""
    pass


class TagListResponse(BaseModel):
    """Tag list response"""
    total: int
    items: list[TagResponse]
