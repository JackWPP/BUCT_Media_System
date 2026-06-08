import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import deps
from app.core.database import Base
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import Photo, PhotoClassification, Tag, User
from app.models.taxonomy import TaxonomyFacet, TaxonomyNode
from app.services.taxonomy import ensure_default_taxonomy, resolve_legacy_photo_classifications
from scripts import migrate_photo_type_fix68


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def flatten_nodes(nodes: list[dict]) -> list[dict]:
    flattened = []
    for node in nodes:
        flattened.append(node)
        flattened.extend(flatten_nodes(node.get("children") or []))
    return flattened


def find_taxonomy_node(taxonomy: list[dict], facet_key: str, node_name: str) -> dict:
    return next(
        node
        for facet in taxonomy if facet["key"] == facet_key
        for node in flatten_nodes(facet["nodes"]) if node["name"] == node_name
    )


async def setup_db(session_factory: async_sessionmaker) -> dict[str, str]:
    async with session_factory() as session:
        admin = User(
            id="admin-user",
            student_id="9001",
            email="admin@example.com",
            hashed_password=get_password_hash("Password123"),
            role="admin",
            is_active=True,
        )
        tagger = User(
            id="tagger-user",
            student_id="9002",
            email="tagger@example.com",
            hashed_password=get_password_hash("Password123"),
            role="tagger",
            is_active=True,
        )
        other = User(
            id="other-user",
            student_id="9003",
            email="other@example.com",
            hashed_password=get_password_hash("Password123"),
            role="user",
            is_active=True,
        )
        photo = Photo(
            id="photo-1",
            uploader_id=admin.id,
            filename="photo.jpg",
            original_path="photos/photo.jpg",
            thumb_path="photos/photo-thumb.jpg",
            width=800,
            height=600,
            file_size=100,
            mime_type="image/jpeg",
            status="approved",
            processing_status="completed",
            views=0,
        )
        session.add_all([admin, tagger, other, photo])
        await ensure_default_taxonomy(session)
        await session.commit()

    return {
        "admin": create_access_token({"sub": "9001"}),
        "tagger": create_access_token({"sub": "9002"}),
        "other": create_access_token({"sub": "9003"}),
    }


@pytest.fixture
def tagging_client(tmp_path: Path):
    db_path = tmp_path / "tagging.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def init_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_database())
    tokens = asyncio.run(setup_db(session_factory))

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[deps.get_db] = override_get_db
    with TestClient(app) as client:
        yield client, tokens, session_factory
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_taxonomy_seed_and_public_guide(tagging_client):
    client, _, _ = tagging_client

    taxonomy = client.get("/api/v1/taxonomy/public")
    guide = client.get("/api/v1/taxonomy/public/guide")

    assert taxonomy.status_code == 200
    facet_names = {facet["key"]: facet["name"] for facet in taxonomy.json()}
    assert facet_names["gallery_series"] == "专区"
    assert facet_names["award_level"] == "奖项"
    assert facet_names["documentary_topic"] == "纪实主题"
    assert facet_names["building"] == "楼宇"
    assert "landmark" not in facet_names
    building_nodes = {
        node["name"]
        for facet in taxonomy.json() if facet["key"] == "building"
        for node in flatten_nodes(facet["nodes"])
    }
    assert "昌平校区楼宇" in building_nodes
    assert "图书馆" in building_nodes
    assert "昌平校区" not in building_nodes
    assert "其它" not in building_nodes
    assert find_taxonomy_node(taxonomy.json(), "building", "昌平校区楼宇")["is_selectable"] is False
    assert find_taxonomy_node(taxonomy.json(), "building", "图书馆")["is_selectable"] is True
    assert guide.status_code == 200
    photo_type_nodes = {
        node["name"]
        for facet in taxonomy.json() if facet["key"] == "photo_type"
        for node in flatten_nodes(facet["nodes"])
    }
    assert photo_type_nodes == {"建筑楼宇", "校区设施", "自然生态"}
    assert guide.json()["dependencies"]["photo_type"]["建筑楼宇"] == ["building", "landscape", "season", "technique"]
    assert guide.json()["dependencies"]["photo_type"]["校区设施"] == ["facility", "landscape", "season", "technique"]


def test_taxonomy_seed_converges_legacy_nodes_to_new_scheme(tagging_client):
    client, _, session_factory = tagging_client

    async def add_legacy_nodes():
        async with session_factory() as session:
            photo = (await session.execute(select(Photo).where(Photo.id == "photo-1"))).scalar_one()

            photo_type_facet = (
                await session.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == "photo_type"))
            ).scalar_one()
            legacy_type = TaxonomyNode(
                facet_id=photo_type_facet.id,
                key="legacy-landscape",
                name="风光",
                is_active=True,
                sort_order=99,
            )
            portrait = TaxonomyNode(
                facet_id=photo_type_facet.id,
                key="legacy-portrait",
                name="人像",
                is_active=True,
                sort_order=100,
            )
            session.add_all([legacy_type, portrait])
            await session.flush()
            session.add(
                PhotoClassification(
                    photo_id=photo.id,
                    facet_id=photo_type_facet.id,
                    node_id=legacy_type.id,
                )
            )

            series_facet = (
                await session.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == "gallery_series"))
            ).scalar_one()
            session.add(
                TaxonomyNode(
                    facet_id=series_facet.id,
                    key="legacy-contest",
                    name="摄影大赛",
                    is_active=True,
                    sort_order=99,
                )
            )

            year_facet = (
                await session.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == "gallery_year"))
            ).scalar_one()
            session.add(
                TaxonomyNode(
                    facet_id=year_facet.id,
                    key="legacy-2018",
                    name="2018",
                    is_active=True,
                    sort_order=99,
                )
            )
            landmark_facet = TaxonomyFacet(
                key="landmark",
                name="旧地标",
                selection_mode="single",
                is_system=True,
                is_active=True,
                sort_order=35,
            )
            session.add(landmark_facet)
            await session.flush()
            session.add(
                TaxonomyNode(
                    facet_id=landmark_facet.id,
                    key="library",
                    name="图书馆",
                    is_active=True,
                    sort_order=1,
                )
            )

            await session.commit()

    async def assert_converged():
        async with session_factory() as session:
            await ensure_default_taxonomy(session)
            await session.commit()

            rows = await session.execute(
                select(TaxonomyFacet.key, TaxonomyNode.name, TaxonomyNode.is_active)
                .join(TaxonomyNode, TaxonomyNode.facet_id == TaxonomyFacet.id)
                .where(TaxonomyNode.name.in_(["风光", "人像", "摄影大赛", "2018", "建筑楼宇", "校园风光"]))
            )
            node_states = {(facet, name): is_active for facet, name, is_active in rows.all()}
            assert node_states[("photo_type", "风光")] is False
            assert node_states[("photo_type", "人像")] is False
            assert node_states[("gallery_series", "摄影大赛")] is False
            assert node_states[("gallery_year", "2018")] is False
            assert node_states[("photo_type", "建筑楼宇")] is True
            if ("photo_type", "校园风光") in node_states:
                assert node_states[("photo_type", "校园风光")] is False
            landmark_facet = (
                await session.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == "landmark"))
            ).scalar_one()
            assert landmark_facet.is_active is False

            classifications = (
                await session.execute(
                    select(TaxonomyNode.name, TaxonomyNode.is_active)
                    .join(PhotoClassification, PhotoClassification.node_id == TaxonomyNode.id)
                    .join(TaxonomyFacet, TaxonomyFacet.id == PhotoClassification.facet_id)
                    .where(PhotoClassification.photo_id == "photo-1", TaxonomyFacet.key == "photo_type")
                )
            ).all()
            assert classifications == [("风光", False)]

    asyncio.run(add_legacy_nodes())
    asyncio.run(assert_converged())

    public_taxonomy = client.get("/api/v1/taxonomy/public").json()
    public_nodes = {
        (facet["key"], node["name"])
        for facet in public_taxonomy
        for node in facet["nodes"]
    }
    assert ("photo_type", "风光") not in public_nodes
    assert ("photo_type", "人像") not in public_nodes
    assert ("gallery_series", "摄影大赛") not in public_nodes
    assert ("gallery_year", "2018") not in public_nodes
    assert ("photo_type", "建筑楼宇") in public_nodes
    assert ("photo_type", "校园风光") not in public_nodes


def test_legacy_photo_type_resolution_uses_fix68_values(tagging_client):
    _client, _tokens, session_factory = tagging_client

    async def resolve_values():
        async with session_factory() as session:
            landscape = await resolve_legacy_photo_classifications(session, category="Landscape")
            documentary = await resolve_legacy_photo_classifications(session, category="Documentary")
            facility = await resolve_legacy_photo_classifications(session, category="校区设施")

            rows = await session.execute(
                select(TaxonomyNode.id, TaxonomyNode.name)
                .join(TaxonomyFacet, TaxonomyFacet.id == TaxonomyNode.facet_id)
                .where(TaxonomyFacet.key == "photo_type")
            )
            node_names = dict(rows.all())
            return (
                node_names.get(landscape.get("photo_type")),
                documentary.get("photo_type"),
                node_names.get(facility.get("photo_type")),
            )

    landscape_name, documentary_node, facility_name = asyncio.run(resolve_values())
    assert landscape_name == "建筑楼宇"
    assert documentary_node is None
    assert facility_name == "校区设施"


def test_new_photo_type_candidate_filters_do_not_use_legacy_category_fallback(tagging_client):
    client, tokens, session_factory = tagging_client

    async def add_facility_photo():
        async with session_factory() as session:
            photo = Photo(
                id="photo-facility",
                uploader_id="admin-user",
                filename="facility.jpg",
                original_path="photos/facility.jpg",
                width=800,
                height=600,
                file_size=100,
                mime_type="image/jpeg",
                status="approved",
                processing_status="completed",
                views=0,
                category="Landscape",
            )
            session.add(photo)
            await session.flush()
            photo_type_facet = (
                await session.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == "photo_type"))
            ).scalar_one()
            facility_node = (
                await session.execute(
                    select(TaxonomyNode).where(
                        TaxonomyNode.facet_id == photo_type_facet.id,
                        TaxonomyNode.name == "校区设施",
                    )
                )
            ).scalar_one()
            session.add(
                PhotoClassification(
                    photo_id=photo.id,
                    facet_id=photo_type_facet.id,
                    node_id=facility_node.id,
                )
            )
            await session.commit()

    asyncio.run(add_facility_photo())

    building_candidates = client.get(
        "/api/v1/tagging-tasks/photo-candidates",
        headers=headers(tokens["admin"]),
        params={
            "selection_mode": "all",
            "photo_type": "建筑楼宇",
        },
    )
    assert building_candidates.status_code == 200
    assert "photo-facility" not in {item["id"] for item in building_candidates.json()["items"]}

    facility_candidates = client.get(
        "/api/v1/tagging-tasks/photo-candidates",
        headers=headers(tokens["admin"]),
        params={
            "selection_mode": "all",
            "photo_type": "校区设施",
        },
    )
    assert facility_candidates.status_code == 200
    assert "photo-facility" in {item["id"] for item in facility_candidates.json()["items"]}


def test_tagger_can_submit_and_admin_approval_writes_photo_data(tagging_client):
    client, tokens, session_factory = tagging_client

    create_response = client.post(
        "/api/v1/tagging-tasks",
        headers=headers(tokens["admin"]),
        json={
            "title": "标注测试",
            "assignee_id": "tagger-user",
            "photo_ids": ["photo-1"],
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["stats"]["pending"] == 1
    item_id = create_response.json()["items"][0]["id"]

    taxonomy = client.get("/api/v1/taxonomy/public").json()
    type_node = find_taxonomy_node(taxonomy, "photo_type", "建筑楼宇")
    series_node = find_taxonomy_node(taxonomy, "gallery_series", "投稿作品")
    source_node = find_taxonomy_node(taxonomy, "source_type", "学生投稿")
    campus_node = find_taxonomy_node(taxonomy, "campus", "昌平校区")
    building_node = find_taxonomy_node(taxonomy, "building", "图书馆")
    building_group_node = find_taxonomy_node(taxonomy, "building", "昌平校区楼宇")
    phenomenon_nodes = [
        node
        for facet in taxonomy if facet["key"] == "natural_phenomenon"
        for node in flatten_nodes(facet["nodes"]) if node["name"] in {"日出", "蓝天"}
    ]
    assert len(phenomenon_nodes) == 2

    denied = client.get("/api/v1/tagging-tasks", headers=headers(tokens["other"]))
    assert denied.status_code == 403

    draft_response = client.post(
        f"/api/v1/tagging-tasks/items/{item_id}/draft",
        headers=headers(tokens["tagger"]),
        json={
            "tags": ["草稿标签"],
            "classifications": {
                "photo_type": type_node["id"],
            },
            "note": "草稿",
        },
    )
    assert draft_response.status_code == 200
    assert draft_response.json()["draft_saved_at"]

    invalid_response = client.post(
        f"/api/v1/tagging-tasks/items/{item_id}/submit",
        headers=headers(tokens["tagger"]),
        json={
            "tags": ["图书馆"],
            "classifications": {
                "photo_type": type_node["id"],
            },
        },
    )
    assert invalid_response.status_code == 400
    assert "专区" in invalid_response.json()["detail"]

    invalid_group_response = client.post(
        f"/api/v1/tagging-tasks/items/{item_id}/submit",
        headers=headers(tokens["tagger"]),
        json={
            "tags": [],
            "classifications": {
                "gallery_series": series_node["id"],
                "source_type": source_node["id"],
                "campus": campus_node["id"],
                "photo_type": type_node["id"],
                "building": [building_group_node["id"]],
            },
        },
    )
    assert invalid_group_response.status_code == 400
    assert "group nodes" in invalid_group_response.json()["detail"]

    submit_response = client.post(
        f"/api/v1/tagging-tasks/items/{item_id}/submit",
        headers=headers(tokens["tagger"]),
        json={
            "tags": [" 图书馆 ", "Library"],
            "classifications": {
                "gallery_series": series_node["id"],
                "source_type": source_node["id"],
                "campus": campus_node["id"],
                "photo_type": type_node["id"],
                "building": [building_node["id"]],
                "natural_phenomenon": [node["id"] for node in phenomenon_nodes],
            },
            "note": "已调整",
        },
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"

    approve_response = client.post(
        f"/api/v1/tagging-tasks/items/{item_id}/approve",
        headers=headers(tokens["admin"]),
        json={"note": "通过"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    async def assert_written():
        async with session_factory() as session:
            tags = (await session.execute(select(Tag.name).order_by(Tag.name))).scalars().all()
            classifications = (await session.execute(select(PhotoClassification))).scalars().all()
            assert "图书馆" in tags
            assert "library" in tags
            assert len(classifications) == 7

    asyncio.run(assert_written())

    filtered = client.get("/api/v1/photos/public?building=图书馆")
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1


def test_batch_review_only_processes_submitted_items_and_updates_stats(tagging_client):
    client, tokens, _ = tagging_client

    create_response = client.post(
        "/api/v1/tagging-tasks",
        headers=headers(tokens["admin"]),
        json={
            "title": "批量审核测试",
            "assignee_id": "tagger-user",
            "photo_ids": ["photo-1"],
        },
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["items"][0]["id"]

    taxonomy = client.get("/api/v1/taxonomy/public").json()
    type_node = find_taxonomy_node(taxonomy, "photo_type", "自然生态")
    series_node = find_taxonomy_node(taxonomy, "gallery_series", "投稿作品")
    source_node = find_taxonomy_node(taxonomy, "source_type", "学生投稿")
    campus_node = find_taxonomy_node(taxonomy, "campus", "昌平校区")

    submitted = client.post(
        f"/api/v1/tagging-tasks/items/{item_id}/submit",
        headers=headers(tokens["tagger"]),
        json={
            "tags": [],
            "classifications": {
                "gallery_series": series_node["id"],
                "source_type": source_node["id"],
                "campus": campus_node["id"],
                "photo_type": type_node["id"],
            },
        },
    )
    assert submitted.status_code == 200

    task = client.get(
        f"/api/v1/tagging-tasks/{create_response.json()['id']}",
        headers=headers(tokens["admin"]),
    ).json()
    assert task["stats"]["submitted"] == 1

    approved = client.post(
        "/api/v1/tagging-tasks/items/batch-approve",
        headers=headers(tokens["admin"]),
        json={"item_ids": [item_id, "missing-item"], "note": "批量通过"},
    )
    assert approved.status_code == 200
    assert len(approved.json()) == 1
    assert approved.json()[0]["status"] == "approved"

    rejected = client.post(
        "/api/v1/tagging-tasks/items/batch-reject",
        headers=headers(tokens["admin"]),
        json={"item_ids": [item_id], "note": "不会重复处理"},
    )
    assert rejected.status_code == 200
    assert rejected.json() == []

    task = client.get(
        f"/api/v1/tagging-tasks/{create_response.json()['id']}",
        headers=headers(tokens["admin"]),
    ).json()
    assert task["stats"]["approved"] == 1
    assert task["stats"]["completion_rate"] == 100


def test_fix68_photo_type_migration_only_maps_deterministic_content(tagging_client):
    _client, _tokens, session_factory = tagging_client

    async def arrange_and_migrate():
        async with session_factory() as session:
            building_photo = (await session.execute(select(Photo).where(Photo.id == "photo-1"))).scalar_one()
            documentary_photo = Photo(
                id="photo-2",
                uploader_id="admin-user",
                filename="activity.jpg",
                original_path="photos/activity.jpg",
                width=800,
                height=600,
                file_size=100,
                mime_type="image/jpeg",
                status="approved",
                processing_status="completed",
                views=0,
            )
            session.add(documentary_photo)
            await session.flush()

            photo_type_facet = (
                await session.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == "photo_type"))
            ).scalar_one()
            old_landscape = TaxonomyNode(
                facet_id=photo_type_facet.id,
                key="old-campus-view",
                name="校园风光",
                is_active=True,
                is_selectable=True,
                sort_order=90,
            )
            old_documentary = TaxonomyNode(
                facet_id=photo_type_facet.id,
                key="old-documentary",
                name="人文纪实",
                is_active=True,
                is_selectable=True,
                sort_order=91,
            )
            session.add_all([old_landscape, old_documentary])
            await session.flush()

            building_facet = (
                await session.execute(select(TaxonomyFacet).where(TaxonomyFacet.key == "building"))
            ).scalar_one()
            library_node = (
                await session.execute(
                    select(TaxonomyNode).where(
                        TaxonomyNode.facet_id == building_facet.id,
                        TaxonomyNode.name == "图书馆",
                    )
                )
            ).scalar_one()
            session.add_all(
                [
                    PhotoClassification(
                        photo_id=building_photo.id,
                        facet_id=photo_type_facet.id,
                        node_id=old_landscape.id,
                    ),
                    PhotoClassification(
                        photo_id=building_photo.id,
                        facet_id=building_facet.id,
                        node_id=library_node.id,
                    ),
                    PhotoClassification(
                        photo_id=documentary_photo.id,
                        facet_id=photo_type_facet.id,
                        node_id=old_documentary.id,
                    ),
                ]
            )
            await session.commit()

        async with session_factory() as session:
            await migrate_photo_type_fix68.migrate(session, apply=True)
            await session.commit()
            rows = await session.execute(
                select(PhotoClassification.photo_id, TaxonomyNode.name)
                .join(TaxonomyNode, TaxonomyNode.id == PhotoClassification.node_id)
                .join(TaxonomyFacet, TaxonomyFacet.id == PhotoClassification.facet_id)
                .where(TaxonomyFacet.key == "photo_type")
                .order_by(PhotoClassification.photo_id)
            )
            return rows.all()

    rows = asyncio.run(arrange_and_migrate())
    assert ("photo-1", "建筑楼宇") in rows
    assert not any(photo_id == "photo-2" for photo_id, _node_name in rows)
    assert ("photo-2", "建筑楼宇") not in rows
