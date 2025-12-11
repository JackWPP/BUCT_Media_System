"""
Photo Pydantic schemas
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class PhotoBase(BaseModel):
    """Base photo schema"""
    filename: str = Field(..., description="Original filename")
    description: Optional[str] = Field(None, max_length=500, description="Photo description")
    season: Optional[str] = Field(None, description="Season: Spring/Summer/Autumn/Winter")
    category: Optional[str] = Field(None, description="Category: Landscape/Portrait/Activity/Documentary")


class PhotoCreate(PhotoBase):
    """Schema for creating a photo"""
    pass


class PhotoUpdate(BaseModel):
    """Schema for updating a photo"""
    description: Optional[str] = Field(None, max_length=500)
    season: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    
    model_config = ConfigDict(extra='forbid')


class PhotoInDB(PhotoBase):
    """Photo in database"""
    id: str
    uploader_id: str
    original_path: str
    processed_path: Optional[str] = None
    thumb_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    exif_data: Optional[Dict[str, Any]] = None
    captured_at: Optional[datetime] = None
    status: str
    processing_status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PhotoResponse(PhotoInDB):
    """Photo response schema"""
    uploader_name: Optional[str] = None
    tags: List[str] = Field(default_factory=list, description="Associated tags")
    
    model_config = ConfigDict(from_attributes=True)


class PhotoListResponse(BaseModel):
    """Photo list response with pagination"""
    total: int
    page: int
    page_size: int
    items: List[PhotoResponse]


class PhotoUploadResponse(BaseModel):
    """Response after uploading a photo"""
    id: str
    filename: str
    original_path: str
    thumb_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    status: str
    message: str = "Photo uploaded successfully"
    
    model_config = ConfigDict(from_attributes=True)
