"""
AI analysis schemas.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AIAnalysisTaskCreate(BaseModel):
    force: bool = Field(default=False, description="Run a new analysis even if a completed result exists.")


class AIAnalysisTaskResponse(BaseModel):
    id: str
    photo_id: str
    requested_by_id: Optional[str]
    reviewed_by_id: Optional[str]
    provider: str
    model_id: str
    status: str
    prompt_version: str
    result_json: Optional[dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    applied_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class AIApplyResponse(BaseModel):
    applied: bool
    task: AIAnalysisTaskResponse
    unresolved_classifications: dict[str, str] = Field(default_factory=dict)
