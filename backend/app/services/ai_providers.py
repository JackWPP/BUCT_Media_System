"""
Helpers for managing and resolving AI provider configs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.secrets import decrypt_secret, encrypt_secret, mask_secret
from app.models.ai_provider import AIProviderConfig, AIProviderType
from app.schemas.ai_provider import (
    AIProviderConfigDetail,
    AIProviderConfigSummary,
    AIProviderCreate,
    AIProviderMaskedSecret,
    AIProviderTestResult,
    AIProviderUpdate,
)

settings = get_settings()


@dataclass
class ResolvedAIProvider:
    provider_type: str
    display_name: str
    base_url: str
    model_id: str
    api_key: str | None
    extra_headers: dict[str, Any]
    timeout_seconds: int
    max_retries: int
    daily_budget: int
    source: str
    provider_id: str | None = None


def _serialize_secret(config: AIProviderConfig) -> AIProviderMaskedSecret:
    api_key = decrypt_secret(config.api_key_encrypted) if config.api_key_encrypted else None
    return AIProviderMaskedSecret(has_api_key=bool(api_key), masked_value=mask_secret(api_key))


def serialize_provider_summary(config: AIProviderConfig) -> AIProviderConfigSummary:
    return AIProviderConfigSummary(
        id=config.id,
        provider_type=config.provider_type,
        display_name=config.display_name,
        enabled=config.enabled,
        is_default=config.is_default,
        base_url=config.base_url,
        model_id=config.model_id,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
        daily_budget=config.daily_budget,
        last_test_status=config.last_test_status,
        last_test_message=config.last_test_message,
        last_tested_at=config.last_tested_at,
        updated_at=config.updated_at,
        secret=_serialize_secret(config),
    )


def serialize_provider_detail(config: AIProviderConfig) -> AIProviderConfigDetail:
    summary = serialize_provider_summary(config)
    return AIProviderConfigDetail(**summary.model_dump(), extra_headers_json=config.extra_headers_json or {})


async def list_ai_provider_configs(db: AsyncSession, enabled_only: bool = False) -> list[AIProviderConfig]:
    query = select(AIProviderConfig).order_by(
        case((AIProviderConfig.is_default.is_(True), 0), else_=1),
        AIProviderConfig.display_name.asc(),
    )
    if enabled_only:
        query = query.where(AIProviderConfig.enabled.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_ai_provider_config(db: AsyncSession, provider_id: str) -> AIProviderConfig | None:
    result = await db.execute(select(AIProviderConfig).where(AIProviderConfig.id == provider_id))
    return result.scalar_one_or_none()


async def _clear_other_defaults(db: AsyncSession, provider_id: str) -> None:
    await db.execute(
        update(AIProviderConfig)
        .where(AIProviderConfig.id != provider_id, AIProviderConfig.is_default.is_(True))
        .values(is_default=False, updated_at=datetime.utcnow())
    )


async def create_ai_provider_config(
    db: AsyncSession,
    payload: AIProviderCreate,
    user_id: str,
) -> AIProviderConfig:
    existing_count = await db.scalar(select(func.count(AIProviderConfig.id)))
    config = AIProviderConfig(
        provider_type=payload.provider_type,
        display_name=payload.display_name,
        enabled=payload.enabled,
        is_default=payload.is_default or (payload.enabled and not existing_count),
        base_url=payload.base_url,
        model_id=payload.model_id,
        api_key_encrypted=encrypt_secret(payload.api_key) if payload.api_key else None,
        extra_headers_json=payload.extra_headers_json or {},
        timeout_seconds=payload.timeout_seconds,
        max_retries=payload.max_retries,
        daily_budget=payload.daily_budget,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(config)
    await db.flush()
    if config.is_default:
        await _clear_other_defaults(db, config.id)
    await db.commit()
    await db.refresh(config)
    return config


async def update_ai_provider_config(
    db: AsyncSession,
    config: AIProviderConfig,
    payload: AIProviderUpdate,
    user_id: str,
) -> AIProviderConfig:
    update_data = payload.model_dump(exclude_unset=True, exclude={"api_key", "clear_api_key"})
    for field, value in update_data.items():
        setattr(config, field, value)

    if payload.clear_api_key:
        config.api_key_encrypted = None
    elif payload.api_key:
        config.api_key_encrypted = encrypt_secret(payload.api_key)

    if payload.is_default:
        config.enabled = True

    config.updated_by = user_id
    config.updated_at = datetime.utcnow()

    await db.flush()
    if payload.is_default:
        await _clear_other_defaults(db, config.id)
    await db.commit()
    await db.refresh(config)
    return config


async def set_default_provider(db: AsyncSession, config: AIProviderConfig, user_id: str) -> AIProviderConfig:
    await _clear_other_defaults(db, config.id)
    config.is_default = True
    config.enabled = True
    config.updated_by = user_id
    config.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(config)
    return config


def _ensure_provider_is_valid(
    provider_type: str,
    base_url: str,
    model_id: str,
    api_key: str | None,
) -> None:
    if provider_type == AIProviderType.DASHSCOPE and not api_key:
        raise ValueError("DashScope requires an API key.")
    if provider_type == AIProviderType.OPENAI_COMPATIBLE and not base_url:
        raise ValueError("OpenAI-compatible base_url is required.")
    if provider_type == AIProviderType.OLLAMA and not base_url:
        raise ValueError("Ollama base_url is required.")
    if not model_id:
        raise ValueError("model_id is required.")


async def test_provider_connection(
    provider_type: str,
    base_url: str,
    model_id: str,
    api_key: str | None,
    extra_headers: dict[str, Any] | None = None,
    timeout_seconds: int = 60,
) -> AIProviderTestResult:
    _ensure_provider_is_valid(provider_type, base_url, model_id, api_key)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update({str(k): str(v) for k, v in extra_headers.items()})
    if api_key:
        headers.setdefault("Authorization", f"Bearer {api_key}")

    checked_at = datetime.utcnow()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            if provider_type == AIProviderType.OLLAMA:
                response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            else:
                response = await client.get(f"{base_url.rstrip('/')}/models", headers=headers)
            response.raise_for_status()
        return AIProviderTestResult(success=True, message="Connection test succeeded.", checked_at=checked_at)
    except httpx.HTTPStatusError as exc:
        detail = f"HTTP {exc.response.status_code}"
        return AIProviderTestResult(success=False, message=f"Connection test failed: {detail}", checked_at=checked_at)
    except Exception as exc:  # noqa: BLE001
        return AIProviderTestResult(success=False, message=f"Connection test failed: {exc}", checked_at=checked_at)


def _env_provider_from_legacy(
    provider_type: str,
    model_id: str,
) -> ResolvedAIProvider | None:
    if provider_type == AIProviderType.DASHSCOPE:
        api_key = settings.DASHSCOPE_API_KEY
        if not api_key:
            return None
        return ResolvedAIProvider(
            provider_type=provider_type,
            display_name="DashScope (env fallback)",
            base_url=settings.DASHSCOPE_BASE_URL,
            model_id=model_id or "qwen-vl-max",
            api_key=api_key,
            extra_headers={},
            timeout_seconds=settings.AI_TIMEOUT,
            max_retries=settings.AI_MAX_RETRIES,
            daily_budget=settings.AI_DAILY_BUDGET,
            source="env",
        )
    if provider_type == AIProviderType.OPENAI_COMPATIBLE:
        if not settings.OPENAI_COMPATIBLE_BASE_URL:
            return None
        api_key = settings.OPENAI_COMPATIBLE_API_KEY
        return ResolvedAIProvider(
            provider_type=provider_type,
            display_name="OpenAI Compatible (env fallback)",
            base_url=settings.OPENAI_COMPATIBLE_BASE_URL,
            model_id=model_id or settings.OPENAI_COMPATIBLE_MODEL_ID or "gpt-4.1-mini",
            api_key=api_key,
            extra_headers=settings.OPENAI_COMPATIBLE_HEADERS,
            timeout_seconds=settings.AI_TIMEOUT,
            max_retries=settings.AI_MAX_RETRIES,
            daily_budget=settings.AI_DAILY_BUDGET,
            source="env",
        )
    return ResolvedAIProvider(
        provider_type=AIProviderType.OLLAMA,
        display_name="Ollama (env fallback)",
        base_url=settings.OLLAMA_API_URL,
        model_id=model_id or settings.AI_MODEL_ID or settings.AI_MODEL_NAME,
        api_key=None,
        extra_headers={},
        timeout_seconds=settings.AI_TIMEOUT,
        max_retries=settings.AI_MAX_RETRIES,
        daily_budget=settings.AI_DAILY_BUDGET,
        source="env",
    )


async def resolve_db_providers(db: AsyncSession) -> list[ResolvedAIProvider]:
    providers = await list_ai_provider_configs(db, enabled_only=True)
    resolved: list[ResolvedAIProvider] = []
    for provider in providers:
        api_key = decrypt_secret(provider.api_key_encrypted) if provider.api_key_encrypted else None
        resolved.append(
            ResolvedAIProvider(
                provider_type=provider.provider_type,
                display_name=provider.display_name,
                base_url=provider.base_url,
                model_id=provider.model_id,
                api_key=api_key,
                extra_headers=provider.extra_headers_json or {},
                timeout_seconds=provider.timeout_seconds,
                max_retries=provider.max_retries,
                daily_budget=provider.daily_budget,
                source="db",
                provider_id=provider.id,
            )
        )
    return resolved


def resolve_env_provider(
    provider_type: str,
    model_id: str,
) -> ResolvedAIProvider | None:
    return _env_provider_from_legacy(provider_type, model_id)
