"""
Runtime settings resolved from environment plus DB-backed overrides.
"""
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.system_config import ConfigKeys, PortraitVisibility, SystemConfig
from app.services.ai_providers import ResolvedAIProvider, resolve_db_providers, resolve_env_provider

settings = get_settings()


@dataclass
class RuntimeSettings:
    portrait_visibility: str
    ai_enabled: bool
    storage_backend: str
    task_queue_backend: str
    database_backend: str
    providers: list[ResolvedAIProvider] = field(default_factory=list)

    @property
    def default_provider(self) -> ResolvedAIProvider | None:
        return self.providers[0] if self.providers else None

    @property
    def ai_provider(self) -> str:
        return self.default_provider.provider_type if self.default_provider else settings.AI_PROVIDER

    @property
    def ai_model_id(self) -> str:
        return self.default_provider.model_id if self.default_provider else (settings.AI_MODEL_ID or settings.AI_MODEL_NAME)

    @property
    def default_provider_type(self) -> str | None:
        return self.default_provider.provider_type if self.default_provider else None

    @property
    def default_provider_base_url(self) -> str | None:
        return self.default_provider.base_url if self.default_provider else None

    @property
    def default_provider_model_id(self) -> str | None:
        return self.default_provider.model_id if self.default_provider else None

    @property
    def provider_timeout(self) -> int | None:
        return self.default_provider.timeout_seconds if self.default_provider else settings.AI_TIMEOUT

    @property
    def provider_retry(self) -> int | None:
        return self.default_provider.max_retries if self.default_provider else settings.AI_MAX_RETRIES

    @property
    def provider_budget(self) -> int | None:
        return self.default_provider.daily_budget if self.default_provider else settings.AI_DAILY_BUDGET


def _parse_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _database_backend_name() -> str:
    database_url = settings.DATABASE_URL.lower()
    if database_url.startswith("postgresql"):
        return "postgresql"
    if database_url.startswith("sqlite"):
        return "sqlite"
    if database_url.startswith("mysql"):
        return "mysql"
    return "other"


async def get_runtime_settings(db: AsyncSession) -> RuntimeSettings:
    result = await db.execute(select(SystemConfig))
    rows = result.scalars().all()
    config_map = {row.key: row.value for row in rows}
    providers = await resolve_db_providers(db)

    if not providers:
        legacy_provider = config_map.get(ConfigKeys.AI_PROVIDER, settings.AI_PROVIDER)
        legacy_model_id = config_map.get(ConfigKeys.AI_MODEL_ID, settings.AI_MODEL_ID or settings.AI_MODEL_NAME)
        env_provider = resolve_env_provider(legacy_provider, legacy_model_id)
        providers = [env_provider] if env_provider else []

    return RuntimeSettings(
        portrait_visibility=config_map.get(ConfigKeys.PORTRAIT_VISIBILITY, PortraitVisibility.LOGIN_REQUIRED),
        ai_enabled=_parse_bool(config_map.get(ConfigKeys.AI_ENABLED), settings.AI_ENABLED),
        storage_backend=settings.STORAGE_BACKEND,
        task_queue_backend=settings.TASK_QUEUE_BACKEND,
        database_backend=_database_backend_name(),
        providers=providers,
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
