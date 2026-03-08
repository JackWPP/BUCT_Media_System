"""
Admin system settings endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin_user, get_db
from app.core.config import get_settings
from app.models.system_config import ConfigKeys, PortraitVisibility
from app.models.user import User
from app.services.runtime_settings import get_runtime_settings, set_runtime_setting

router = APIRouter(prefix="/settings")
settings = get_settings()


class PortraitVisibilityUpdate(BaseModel):
    visibility: str

    model_config = ConfigDict(json_schema_extra={"example": {"visibility": "login_required"}})


class AISettingsUpdate(BaseModel):
    enabled: bool
    provider: str
    model_id: str

    model_config = ConfigDict(protected_namespaces=())


class AdminSystemSettings(BaseModel):
    portrait_visibility: str
    ai_enabled: bool
    ai_provider: str
    ai_model_id: str
    storage_backend: str
    task_queue_backend: str


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


def _validate_ai_provider(provider: str) -> None:
    if provider not in {"ollama", "dashscope"}:
        raise HTTPException(status_code=400, detail="Invalid AI provider.")
    if provider == "dashscope" and not settings.DASHSCOPE_API_KEY:
        raise HTTPException(status_code=400, detail="DASHSCOPE_API_KEY is not configured on the server.")


@router.get("", response_model=AdminSystemSettings)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    runtime_settings = await get_runtime_settings(db)
    return AdminSystemSettings(
        portrait_visibility=runtime_settings.portrait_visibility,
        ai_enabled=runtime_settings.ai_enabled,
        ai_provider=runtime_settings.ai_provider,
        ai_model_id=runtime_settings.ai_model_id,
        storage_backend=runtime_settings.storage_backend,
        task_queue_backend=runtime_settings.task_queue_backend,
    )


@router.put("/portrait-visibility", response_model=AdminSystemSettings)
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
    return AdminSystemSettings(
        portrait_visibility=runtime_settings.portrait_visibility,
        ai_enabled=runtime_settings.ai_enabled,
        ai_provider=runtime_settings.ai_provider,
        ai_model_id=runtime_settings.ai_model_id,
        storage_backend=runtime_settings.storage_backend,
        task_queue_backend=runtime_settings.task_queue_backend,
    )


@router.put("/ai", response_model=AdminSystemSettings)
async def update_ai_settings(
    data: AISettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    _validate_ai_provider(data.provider)
    await set_runtime_setting(
        db,
        ConfigKeys.AI_ENABLED,
        "true" if data.enabled else "false",
        updated_by=current_user.id,
        description="Whether AI analysis is enabled",
    )
    await set_runtime_setting(
        db,
        ConfigKeys.AI_PROVIDER,
        data.provider,
        updated_by=current_user.id,
        description="AI provider override",
    )
    await set_runtime_setting(
        db,
        ConfigKeys.AI_MODEL_ID,
        data.model_id,
        updated_by=current_user.id,
        description="AI model override",
    )
    runtime_settings = await get_runtime_settings(db)
    return AdminSystemSettings(
        portrait_visibility=runtime_settings.portrait_visibility,
        ai_enabled=runtime_settings.ai_enabled,
        ai_provider=runtime_settings.ai_provider,
        ai_model_id=runtime_settings.ai_model_id,
        storage_backend=runtime_settings.storage_backend,
        task_queue_backend=runtime_settings.task_queue_backend,
    )


@router.get("/portrait-visibility")
async def get_portrait_visibility_public(
    db: AsyncSession = Depends(get_db),
):
    runtime_settings = await get_runtime_settings(db)
    return {"portrait_visibility": runtime_settings.portrait_visibility}
