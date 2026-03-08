import asyncio
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.endpoints import admin_config
from app.core import deps
from app.core.database import Base
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import User


def create_auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "admin-settings.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def init_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def seed_database():
        async with session_factory() as session:
            admin = User(
                id="admin-user",
                student_id="20269999",
                email="admin@buct.edu.cn",
                hashed_password=get_password_hash("password123"),
                full_name="Admin",
                role="admin",
                is_active=True,
            )
            session.add(admin)
            await session.commit()

    asyncio.run(init_database())
    asyncio.run(seed_database())

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    async def fake_test_provider_connection(**kwargs):
        return admin_config.AIProviderTestResult(
            success=True,
            message="Connection test succeeded.",
            checked_at=datetime.utcnow(),
        )

    monkeypatch.setattr(admin_config, "test_provider_connection", fake_test_provider_connection)
    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_admin_can_create_provider_and_get_masked_secret(admin_client):
    token = create_access_token({"sub": "20269999"})
    headers = create_auth_headers(token)

    create_response = admin_client.post(
        "/api/v1/admin/ai-providers",
        headers=headers,
        json={
            "provider_type": "dashscope",
            "display_name": "DashScope Prod",
            "enabled": True,
            "is_default": True,
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_id": "qwen-vl-max",
            "api_key": "sk-test-12345678",
            "extra_headers_json": {},
            "timeout_seconds": 60,
            "max_retries": 2,
            "daily_budget": 500,
        },
    )

    assert create_response.status_code == 201
    provider_id = create_response.json()["id"]
    assert create_response.json()["secret"]["has_api_key"] is True
    assert create_response.json()["secret"]["masked_value"].startswith("sk-")

    list_response = admin_client.get("/api/v1/admin/ai-providers", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == provider_id
    assert list_response.json()[0]["secret"]["has_api_key"] is True

    settings_response = admin_client.get("/api/v1/admin/settings", headers=headers)
    assert settings_response.status_code == 200
    assert settings_response.json()["default_provider"]["provider_type"] == "dashscope"
    assert settings_response.json()["default_provider"]["model_id"] == "qwen-vl-max"


def test_admin_can_test_and_toggle_provider(admin_client):
    token = create_access_token({"sub": "20269999"})
    headers = create_auth_headers(token)

    create_response = admin_client.post(
        "/api/v1/admin/ai-providers",
        headers=headers,
        json={
            "provider_type": "ollama",
            "display_name": "Local Ollama",
            "enabled": True,
            "base_url": "http://localhost:11434",
            "model_id": "llava",
            "extra_headers_json": {},
            "timeout_seconds": 60,
            "max_retries": 1,
            "daily_budget": 0,
        },
    )
    provider_id = create_response.json()["id"]

    test_response = admin_client.post(f"/api/v1/admin/ai-providers/{provider_id}/test", headers=headers)
    assert test_response.status_code == 200
    assert test_response.json()["success"] is True

    toggle_response = admin_client.post(
        f"/api/v1/admin/ai-providers/{provider_id}/toggle",
        headers=headers,
        json={"enabled": False},
    )
    assert toggle_response.status_code == 200
    assert toggle_response.json()["enabled"] is False
