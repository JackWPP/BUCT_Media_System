"""
Schemas for student tagging tasks.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.photo import PhotoResponse


class TaggingTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assignee_id: str
    photo_ids: list[str] = Field(default_factory=list, min_length=1)


class TaggingTaskBatchCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assignee_ids: list[str] = Field(default_factory=list, min_length=1)
    photo_ids: list[str] = Field(default_factory=list)
    selection_mode: str = Field(default="manual", pattern="^(manual|all|zero_tags)$")
    status: Optional[str] = "approved"
    search: Optional[str] = None
    photo_type: Optional[str] = Field(default=None, pattern="^(风光类|纪实类|校园风光|人文纪实|自然生态)$")
    max_photos: int = Field(default=5000, ge=1, le=20000)


class TaggingTaskItemSubmit(BaseModel):
    tags: list[str] = Field(default_factory=list)
    classifications: dict[str, int | list[int]] = Field(default_factory=dict)
    note: Optional[str] = None


class TaggingTaskItemReview(BaseModel):
    note: Optional[str] = None


class TaggingTaskItemResponse(BaseModel):
    id: str
    task_id: str
    photo_id: str
    status: str
    original_tags: list[str] | None = None
    submitted_tags: list[str] | None = None
    original_classifications: dict[str, Any] | None = None
    submitted_classifications: dict[str, Any] | None = None
    submitter_note: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_note: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    photo: Optional[PhotoResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TaggingTaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    creator_id: str
    assignee_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    items: list[TaggingTaskItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TaggingTaskListResponse(BaseModel):
    total: int
    items: list[TaggingTaskResponse]


class TaggingPhotoCandidateListResponse(BaseModel):
    total: int
    items: list[PhotoResponse]
