"""
Admin system settings and AI provider management endpoints.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin_user, get_db
from app.models.ai_provider import AIProviderType
from app.models.system_config import ConfigKeys, PortraitVisibility
from app.models.user import User
from app.schemas.ai_provider import (
    AIProviderConfigDetail,
    AIProviderConfigSummary,
    AIProviderCreate,
    AIProviderTestResult,
    AIProviderToggleRequest,
    AIProviderUpdate,
)
from app.services.ai_providers import (
    create_ai_provider_config,
    get_ai_provider_config,
    list_ai_provider_configs,
    serialize_provider_detail,
    serialize_provider_summary,
    set_default_provider,
    test_provider_connection,
    update_ai_provider_config,
)
from app.services.runtime_settings import get_runtime_settings, set_runtime_setting

router = APIRouter()


class PortraitVisibilityUpdate(BaseModel):
    visibility: str

    model_config = ConfigDict(json_schema_extra={"example": {"visibility": "login_required"}})


class AISettingsUpdate(BaseModel):
    enabled: bool


class RuntimeProviderSummary(BaseModel):
    provider_type: str
    display_name: str
    model_id: str
    base_url: str
    source: str
    timeout_seconds: int
    max_retries: int
    daily_budget: int

    model_config = ConfigDict(protected_namespaces=())


class AdminSystemSettings(BaseModel):
    portrait_visibility: str
    ai_enabled: bool
    storage_backend: str
    task_queue_backend: str
    database_backend: str
    default_provider: RuntimeProviderSummary | None = None


def _validate_portrait_visibility(value: str) -> None:
    valid_values = [
        PortraitVisibility.PUBLIC,
        PortraitVisibility.LOGIN_REQUIRED,
        PortraitVisibility.AUTHORIZED_ONLY,
    ]
    if value not in valid_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid portrait visibility. Expected one of: {', '.join(valid_values)}",
        )


def _runtime_summary(runtime_settings) -> AdminSystemSettings:
    provider = runtime_settings.default_provider
    return AdminSystemSettings(
        portrait_visibility=runtime_settings.portrait_visibility,
        ai_enabled=runtime_settings.ai_enabled,
        storage_backend=runtime_settings.storage_backend,
        task_queue_backend=runtime_settings.task_queue_backend,
        database_backend=runtime_settings.database_backend,
        default_provider=RuntimeProviderSummary(
            provider_type=provider.provider_type,
            display_name=provider.display_name,
            model_id=provider.model_id,
            base_url=provider.base_url,
            source=provider.source,
            timeout_seconds=provider.timeout_seconds,
            max_retries=provider.max_retries,
            daily_budget=provider.daily_budget,
        ) if provider else None,
    )


@router.get("/settings", response_model=AdminSystemSettings)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    runtime_settings = await get_runtime_settings(db)
    return _runtime_summary(runtime_settings)


@router.put("/settings/portrait-visibility", response_model=AdminSystemSettings)
async def update_portrait_visibility(
    data: PortraitVisibilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    _validate_portrait_visibility(data.visibility)
    await set_runtime_setting(
        db,
        ConfigKeys.PORTRAIT_VISIBILITY,
        data.visibility,
        updated_by=current_user.id,
        description="Portrait visibility policy",
    )
    runtime_settings = await get_runtime_settings(db)
    return _runtime_summary(runtime_settings)


@router.put("/settings/ai", response_model=AdminSystemSettings)
async def update_ai_settings(
    data: AISettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    await set_runtime_setting(
        db,
        ConfigKeys.AI_ENABLED,
        "true" if data.enabled else "false",
        updated_by=current_user.id,
        description="Whether AI analysis is enabled",
    )
    runtime_settings = await get_runtime_settings(db)
    return _runtime_summary(runtime_settings)


@router.get("/settings/portrait-visibility")
async def get_portrait_visibility_public(
    db: AsyncSession = Depends(get_db),
):
    runtime_settings = await get_runtime_settings(db)
    return {"portrait_visibility": runtime_settings.portrait_visibility}


@router.get("/ai-providers", response_model=list[AIProviderConfigSummary])
async def get_ai_providers(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    providers = await list_ai_provider_configs(db)
    return [serialize_provider_summary(item) for item in providers]


@router.get("/ai-providers/{provider_id}", response_model=AIProviderConfigDetail)
async def get_ai_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    provider = await get_ai_provider_config(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="AI provider not found.")
    return serialize_provider_detail(provider)


@router.post("/ai-providers", response_model=AIProviderConfigDetail, status_code=status.HTTP_201_CREATED)
async def create_ai_provider(
    payload: AIProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    if payload.provider_type not in AIProviderType.ALL:
        raise HTTPException(status_code=400, detail="Unsupported AI provider type.")
    provider = await create_ai_provider_config(db, payload, current_user.id)
    return serialize_provider_detail(provider)


@router.put("/ai-providers/{provider_id}", response_model=AIProviderConfigDetail)
async def update_ai_provider(
    provider_id: str,
    payload: AIProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    provider = await get_ai_provider_config(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="AI provider not found.")
    provider = await update_ai_provider_config(db, provider, payload, current_user.id)
    return serialize_provider_detail(provider)


@router.post("/ai-providers/{provider_id}/test", response_model=AIProviderTestResult)
async def test_ai_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    provider = await get_ai_provider_config(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="AI provider not found.")
    from app.core.secrets import decrypt_secret

    test_result = await test_provider_connection(
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        model_id=provider.model_id,
        api_key=decrypt_secret(provider.api_key_encrypted) if provider.api_key_encrypted else None,
        extra_headers=provider.extra_headers_json or {},
        timeout_seconds=provider.timeout_seconds,
    )

    provider.last_test_status = "success" if test_result.success else "failed"
    provider.last_test_message = test_result.message
    provider.last_tested_at = test_result.checked_at
    provider.updated_by = current_user.id
    provider.updated_at = datetime.utcnow()
    await db.commit()
    return test_result


@router.post("/ai-providers/{provider_id}/set-default", response_model=AIProviderConfigDetail)
async def set_ai_provider_default(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    provider = await get_ai_provider_config(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="AI provider not found.")
    provider = await set_default_provider(db, provider, current_user.id)
    return serialize_provider_detail(provider)


@router.post("/ai-providers/{provider_id}/toggle", response_model=AIProviderConfigDetail)
async def toggle_ai_provider(
    provider_id: str,
    payload: AIProviderToggleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    provider = await get_ai_provider_config(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="AI provider not found.")
    provider.enabled = payload.enabled
    if not payload.enabled and provider.is_default:
        provider.is_default = False
    provider.updated_by = current_user.id
    provider.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(provider)
    return serialize_provider_detail(provider)
