"""
Runtime settings resolved from environment plus DB-backed overrides.
"""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.system_config import ConfigKeys, PortraitVisibility, SystemConfig

settings = get_settings()


@dataclass
class RuntimeSettings:
    portrait_visibility: str
    ai_enabled: bool
    ai_provider: str
    ai_model_id: str
    storage_backend: str
    task_queue_backend: str


def _parse_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


async def get_runtime_settings(db: AsyncSession) -> RuntimeSettings:
    result = await db.execute(select(SystemConfig))
    rows = result.scalars().all()
    config_map = {row.key: row.value for row in rows}

    return RuntimeSettings(
        portrait_visibility=config_map.get(ConfigKeys.PORTRAIT_VISIBILITY, PortraitVisibility.LOGIN_REQUIRED),
        ai_enabled=_parse_bool(config_map.get(ConfigKeys.AI_ENABLED), settings.AI_ENABLED),
        ai_provider=config_map.get(ConfigKeys.AI_PROVIDER, settings.AI_PROVIDER),
        ai_model_id=config_map.get(ConfigKeys.AI_MODEL_ID, settings.AI_MODEL_ID or settings.AI_MODEL_NAME),
        storage_backend=settings.STORAGE_BACKEND,
        task_queue_backend=settings.TASK_QUEUE_BACKEND,
    )


async def set_runtime_setting(
    db: AsyncSession,
    key: str,
    value: str,
    updated_by: str | None = None,
    description: str | None = None,
) -> SystemConfig:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    if config is None:
        config = SystemConfig(
            key=key,
            value=value,
            description=description or f"Runtime config for {key}",
            updated_by=updated_by,
        )
        db.add(config)
    else:
        config.value = value
        config.updated_by = updated_by
        if description:
            config.description = description
    await db.commit()
    await db.refresh(config)
    return config
