import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import deps
from app.core.database import Base
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import ConfigKeys, Photo, SystemConfig, User
from app.models.system_config import PortraitVisibility


def create_auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def setup_database(session_factory: async_sessionmaker, uploads_dir: Path) -> dict[str, str]:
    original_dir = uploads_dir / "originals"
    thumbnail_dir = uploads_dir / "thumbnails"
    original_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    portrait_original = original_dir / "portrait.jpg"
    portrait_thumb = thumbnail_dir / "portrait_thumb.jpg"
    pending_original = original_dir / "pending.jpg"
    pending_thumb = thumbnail_dir / "pending_thumb.jpg"

    portrait_original.write_bytes(b"portrait")
    portrait_thumb.write_bytes(b"portrait-thumb")
    pending_original.write_bytes(b"pending")
    pending_thumb.write_bytes(b"pending-thumb")

    async with session_factory() as session:
        owner = User(
            id="owner-user",
            student_id="20260001",
            email="owner@buct.edu.cn",
            hashed_password=get_password_hash("password123"),
            full_name="Owner",
            role="user",
            is_active=True,
        )
        other_user = User(
            id="other-user",
            student_id="20260002",
            email="other@buct.edu.cn",
            hashed_password=get_password_hash("password123"),
            full_name="Other",
            role="user",
            is_active=True,
        )
        auditor = User(
            id="auditor-user",
            student_id="20260003",
            email="auditor@buct.edu.cn",
            hashed_password=get_password_hash("password123"),
            full_name="Auditor",
            role="auditor",
            is_active=True,
        )
        admin = User(
            id="admin-user",
            student_id="20260004",
            email="admin@buct.edu.cn",
            hashed_password=get_password_hash("password123"),
            full_name="Admin",
            role="admin",
            is_active=True,
        )
        session.add_all([owner, other_user, auditor, admin])

        portrait_photo = Photo(
            id="portrait-photo",
            uploader_id=owner.id,
            filename="portrait.jpg",
            original_path=f"originals/portrait.jpg",
            thumb_path=f"thumbnails/portrait_thumb.jpg",
            width=1200,
            height=800,
            file_size=portrait_original.stat().st_size,
            mime_type="image/jpeg",
            category="Portrait",
            status="approved",
            processing_status="completed",
            views=0,
        )
        pending_photo = Photo(
            id="pending-photo",
            uploader_id=owner.id,
            filename="pending.jpg",
            original_path=f"originals/pending.jpg",
            thumb_path=f"thumbnails/pending_thumb.jpg",
            width=1000,
            height=700,
            file_size=pending_original.stat().st_size,
            mime_type="image/jpeg",
            category="Landscape",
            status="pending",
            processing_status="completed",
            views=0,
        )
        session.add_all([portrait_photo, pending_photo])

        session.add(
            SystemConfig(
                key=ConfigKeys.PORTRAIT_VISIBILITY,
                value=PortraitVisibility.AUTHORIZED_ONLY,
                description="Test portrait visibility",
            )
        )

        await session.commit()

    return {
        "owner_token": create_access_token({"sub": "20260001"}),
        "other_token": create_access_token({"sub": "20260002"}),
        "auditor_token": create_access_token({"sub": "20260003"}),
        "admin_token": create_access_token({"sub": "20260004"}),
        "portrait_photo_id": "portrait-photo",
        "pending_photo_id": "pending-photo",
    }


@pytest.fixture
def permission_client(tmp_path: Path):
    db_path = tmp_path / "permissions.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def init_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_database())
    test_data = asyncio.run(setup_database(session_factory, tmp_path / "uploads"))

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as client:
        yield client, test_data

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_regular_user_cannot_list_all_photos(permission_client):
    client, data = permission_client

    response = client.get("/api/v1/photos", headers=create_auth_headers(data["other_token"]))

    assert response.status_code == 403


def test_regular_user_cannot_view_other_users_photo(permission_client):
    client, data = permission_client

    response = client.get(
        f"/api/v1/photos/{data['pending_photo_id']}",
        headers=create_auth_headers(data["other_token"]),
    )

    assert response.status_code == 403


def test_guest_cannot_access_restricted_public_photo_or_files(permission_client):
    client, data = permission_client

    detail_response = client.get(f"/api/v1/photos/public/{data['portrait_photo_id']}")
    original_response = client.get(f"/api/v1/photos/{data['portrait_photo_id']}/image/original")
    thumbnail_response = client.get(f"/api/v1/photos/{data['portrait_photo_id']}/image/thumbnail")
    download_response = client.get(f"/api/v1/photos/{data['portrait_photo_id']}/download")

    assert detail_response.status_code == 404
    assert original_response.status_code == 404
    assert thumbnail_response.status_code == 404
    assert download_response.status_code == 404


def test_owner_can_view_own_pending_photo_and_files(permission_client):
    client, data = permission_client
    token = data["owner_token"]
    photo_id = data["pending_photo_id"]

    detail_response = client.get(
        f"/api/v1/photos/{photo_id}",
        headers=create_auth_headers(token),
    )
    original_response = client.get(
        f"/api/v1/photos/{photo_id}/image/original?access_token={token}"
    )
    thumbnail_response = client.get(
        f"/api/v1/photos/{photo_id}/image/thumbnail?access_token={token}"
    )

    assert detail_response.status_code == 200
    assert original_response.status_code == 200
    assert thumbnail_response.status_code == 200


def test_auditor_can_list_and_review_photos(permission_client):
    client, data = permission_client
    headers = create_auth_headers(data["auditor_token"])

    list_response = client.get("/api/v1/photos", headers=headers)
    approve_response = client.post(
        f"/api/v1/photos/{data['pending_photo_id']}/approve",
        headers=headers,
    )
    batch_reject_response = client.post(
        "/api/v1/photos/batch-reject",
        headers=headers,
        json=[data["pending_photo_id"]],
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 2
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert batch_reject_response.status_code == 200
    assert batch_reject_response.json()["updated_count"] == 1


def test_regular_user_cannot_batch_delete(permission_client):
    client, data = permission_client

    response = client.post(
        "/api/v1/photos/batch-delete",
        headers=create_auth_headers(data["other_token"]),
        json=[data["pending_photo_id"]],
    )

    assert response.status_code == 403


def test_admin_can_batch_delete(permission_client):
    client, data = permission_client

    response = client.post(
        "/api/v1/photos/batch-delete",
        headers=create_auth_headers(data["admin_token"]),
        json=[data["pending_photo_id"]],
    )

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1
