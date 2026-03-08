"""
Schemas for admin-managed AI provider configs.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.ai_provider import AIProviderType


class AIProviderMaskedSecret(BaseModel):
    has_api_key: bool
    masked_value: str | None = None


class AIProviderBase(BaseModel):
    provider_type: str = Field(..., max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True
    base_url: str = Field(..., min_length=1, max_length=500)
    model_id: str = Field(..., min_length=1, max_length=200)
    extra_headers_json: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    max_retries: int = Field(default=2, ge=0, le=5)
    daily_budget: int = Field(default=500, ge=0, le=100000)

    model_config = ConfigDict(protected_namespaces=())

    @field_validator("provider_type")
    @classmethod
    def validate_provider_type(cls, value: str) -> str:
        if value not in AIProviderType.ALL:
            raise ValueError(f"Unsupported provider_type: {value}")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        clean = value.strip()
        if not clean.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return clean.rstrip("/")

    @field_validator("display_name", "model_id")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class AIProviderCreate(AIProviderBase):
    api_key: str | None = None
    is_default: bool = False


class AIProviderUpdate(BaseModel):
    provider_type: str | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    extra_headers_json: dict[str, Any] | None = None
    timeout_seconds: int | None = Field(default=None, ge=5, le=300)
    max_retries: int | None = Field(default=None, ge=0, le=5)
    daily_budget: int | None = Field(default=None, ge=0, le=100000)
    api_key: str | None = None
    clear_api_key: bool = False
    is_default: bool | None = None

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    @field_validator("provider_type")
    @classmethod
    def validate_provider_type(cls, value: str | None) -> str | None:
        if value is not None and value not in AIProviderType.ALL:
            raise ValueError(f"Unsupported provider_type: {value}")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_optional_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        if not clean.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return clean.rstrip("/")

    @field_validator("display_name", "model_id")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class AIProviderToggleRequest(BaseModel):
    enabled: bool


class AIProviderConfigSummary(BaseModel):
    id: str
    provider_type: str
    display_name: str
    enabled: bool
    is_default: bool
    base_url: str
    model_id: str
    timeout_seconds: int
    max_retries: int
    daily_budget: int
    last_test_status: str | None = None
    last_test_message: str | None = None
    last_tested_at: datetime | None = None
    updated_at: datetime
    secret: AIProviderMaskedSecret

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class AIProviderConfigDetail(AIProviderConfigSummary):
    extra_headers_json: dict[str, Any] = Field(default_factory=dict)


class AIProviderTestResult(BaseModel):
    success: bool
    message: str
    checked_at: datetime
