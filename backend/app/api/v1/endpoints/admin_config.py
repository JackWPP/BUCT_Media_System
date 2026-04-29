"""
Admin system settings and AI provider management endpoints.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings as get_core_settings
from app.core.database import Base, engine
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

logger = logging.getLogger(__name__)

router = APIRouter()


class PortraitVisibilityUpdate(BaseModel):
    visibility: str

    model_config = ConfigDict(json_schema_extra={"example": {"visibility": "login_required"}})


class AISettingsUpdate(BaseModel):
    enabled: bool


class AISearchSettingsUpdate(BaseModel):
    enabled: bool
    provider: str | None = None
    model_id: str | None = None


class MigrateToPostgresRequest(BaseModel):
    target_dsn: str = Field(
        ...,
        description="PostgreSQL DSN, e.g. postgresql://user:pass@host:5432/dbname",
        examples=["postgresql://postgres:password@localhost:5432/visual_buct"],
    )
    truncate: bool = Field(False, description="Truncate target tables before importing")


class DatabaseInfo(BaseModel):
    backend: str
    table_count: int
    row_counts: dict[str, int]
    file_size_mb: float | None = None
    alembic_revision: str | None = None


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
    ai_search_enabled: bool
    ai_search_provider: str | None = None
    ai_search_model_id: str | None = None
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
        ai_search_enabled=runtime_settings.ai_search_enabled,
        ai_search_provider=runtime_settings.ai_search_provider,
        ai_search_model_id=runtime_settings.ai_search_model_id,
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


@router.put("/settings/ai-search", response_model=AdminSystemSettings)
async def update_ai_search_settings(
    data: AISearchSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    await set_runtime_setting(
        db,
        ConfigKeys.AI_SEARCH_ENABLED,
        "true" if data.enabled else "false",
        updated_by=current_user.id,
        description="Whether AI smart search is enabled",
    )
    if data.provider is not None:
        await set_runtime_setting(
            db,
            ConfigKeys.AI_SEARCH_PROVIDER,
            data.provider,
            updated_by=current_user.id,
            description="AI search dedicated provider type",
        )
    if data.model_id is not None:
        await set_runtime_setting(
            db,
            ConfigKeys.AI_SEARCH_MODEL_ID,
            data.model_id,
            updated_by=current_user.id,
            description="AI search dedicated model ID",
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


@router.get("/database/info", response_model=DatabaseInfo)
async def get_database_info(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    """Get current database metadata — backend type, row counts, file size."""
    settings = get_core_settings()
    db_url = settings.DATABASE_URL

    # Determine backend type
    if db_url.startswith("sqlite"):
        backend = "sqlite"
    elif db_url.startswith("postgresql"):
        backend = "postgresql"
    else:
        backend = db_url.split("://")[0] if "://" in db_url else "unknown"

    # Get row counts for all user tables
    table_names = sorted(Base.metadata.tables.keys())
    row_counts: dict[str, int] = {}
    for table_name in table_names:
        try:
            result = await db.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            count = result.scalar()
            row_counts[table_name] = count
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to count rows for table %s: %s", table_name, exc
            )
            row_counts[table_name] = -1

    # Get file size (SQLite only)
    file_size_mb = None
    if backend == "sqlite":
        db_path = db_url.split(":///")[-1] if ":///" in db_url else db_url
        path = Path(db_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.exists():
            file_size_mb = round(path.stat().st_size / (1024 * 1024), 2)

    # Get Alembic revision
    alembic_revision = None
    try:
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        row = result.fetchone()
        if row:
            alembic_revision = row[0]
    except Exception:
        pass

    return DatabaseInfo(
        backend=backend,
        table_count=len(table_names),
        row_counts=row_counts,
        file_size_mb=file_size_mb,
        alembic_revision=alembic_revision,
    )


@router.get("/database/migration-script")
async def download_migration_script(
    _current_user: User = Depends(get_current_admin_user),
):
    """Download the SQLite→PostgreSQL migration script."""
    # Path: app/api/v1/endpoints/admin_config.py → 4 levels up to backend/
    script_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "scripts" / "migrate_to_postgres.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Migration script not found")
    return FileResponse(
        path=str(script_path),
        media_type="text/x-python",
        filename="migrate_to_postgres.py",
    )


@router.post("/database/migrate-to-postgres")
async def trigger_migration(
    payload: MigrateToPostgresRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
):
    """Trigger a SQLite→PostgreSQL data migration in the background."""
    import re

    from sqlalchemy import create_engine

    settings = get_core_settings()

    # Determine source path from current DATABASE_URL
    db_url = settings.DATABASE_URL
    if not db_url.startswith("sqlite"):
        raise HTTPException(
            status_code=400,
            detail="Current database must be SQLite to run this migration",
        )
    source_path = db_url.split(":///")[-1] if ":///" in db_url else db_url
    source = Path(source_path)
    if not source.is_absolute():
        source = Path.cwd() / source
    if not source.exists():
        raise HTTPException(status_code=404, detail=f"Source database not found: {source}")

    # Validate target PostgreSQL connection
    dsn = re.sub(r"^postgresql(\+[^:]+)?(?=://)", "postgresql+psycopg2", payload.target_dsn)
    try:
        test_engine = create_engine(dsn)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot connect to target PostgreSQL: {exc}",
        )

    logger.info(
        "Database migration triggered by %s: SQLite %s → PostgreSQL %s (truncate=%s)",
        current_user.student_id,
        source,
        payload.target_dsn,
        payload.truncate,
    )

    # Run migration in background
    def _run_migration() -> None:
        from scripts.migrate_to_postgres import migrate

        def _log(msg: str) -> None:
            logger.info("[migrate] %s", msg)

        try:
            stats = migrate(
                source_path=str(source),
                target_dsn=payload.target_dsn,
                dry_run=False,
                truncate=payload.truncate,
                progress_callback=_log,
            )
            logger.info("Migration complete: %s", stats)
        except Exception as exc:
            logger.exception("Migration failed: %s", exc)

    background_tasks.add_task(_run_migration)

    return {
        "status": "started",
        "message": (
            f"Migration from {source.name} to PostgreSQL running in background. "
            "Check server logs for progress."
        ),
    }


@router.get("/database/export")
async def export_database(
    _current_user: User = Depends(get_current_admin_user),
):
    """Admin-only: download the SQLite database file for migration."""
    db_url = get_core_settings().DATABASE_URL
    # Extract file path from "sqlite+aiosqlite:///./visual_buct.db"
    db_path = db_url.split(":///")[-1] if ":///" in db_url else db_url
    path = Path(db_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Database file not found: {path}")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return FileResponse(
        path=str(path),
        media_type="application/octet-stream",
        filename=f"visual_buct_backup_{timestamp}.db",
    )
