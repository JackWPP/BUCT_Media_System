from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.user import User
from app.services.taxonomy import ensure_default_taxonomy, resolve_taxonomy_node, set_photo_classification


async def resolve_uploader_id(
    *,
    uploader_id: str | None,
    uploader_student_id: str | None,
) -> str:
    async with AsyncSessionLocal() as db:
        if uploader_id:
            user = await db.get(User, uploader_id)
            if user is None:
                raise RuntimeError(f"Uploader id not found: {uploader_id}")
            return str(user.id)

        if uploader_student_id:
            result = await db.execute(select(User).where(User.student_id == uploader_student_id))
            user = result.scalar_one_or_none()
            if user is None:
                raise RuntimeError(f"Uploader student_id not found: {uploader_student_id}")
            return str(user.id)

        result = await db.execute(select(User).where(User.role == "admin").order_by(User.created_at.asc()))
        user = result.scalars().first()
        if user is None:
            raise RuntimeError("No admin user found. Use --uploader-id or --uploader-student-id.")
        return str(user.id)


async def import_manifest(manifest_path: Path, *, uploader_id: str, approved: bool) -> tuple[int, int]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    imported = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        await ensure_default_taxonomy(db)
        for item in items:
            existing = await db.get(Photo, item["photo_id"])
            if existing is not None:
                skipped += 1
                continue

            now = datetime.utcnow()
            captured_at = datetime.fromisoformat(item["captured_at"]) if item.get("captured_at") else None
            photo = Photo(
                id=item["photo_id"],
                uploader_id=uploader_id,
                filename=item["filename"],
                original_path=item["original_path"],
                thumb_path=item.get("thumb_path"),
                compressed_path=item.get("compressed_path"),
                width=item.get("width"),
                height=item.get("height"),
                file_size=item.get("file_size"),
                mime_type=item.get("mime_type"),
                season=None,
                category=item.get("category"),
                campus=item.get("campus"),
                description=item.get("description"),
                exif_data=item.get("exif_data") or {},
                status="approved" if approved else "pending",
                processing_status="manual",
                captured_at=captured_at,
                published_at=now if approved else None,
                created_at=now,
                updated_at=now,
                views=0,
            )
            db.add(photo)
            await db.flush()

            for facet_key, node_name in (item.get("classifications") or {}).items():
                node = await resolve_taxonomy_node(db, facet_key, node_name)
                if node is None:
                    raise RuntimeError(f"Taxonomy node not found: {facet_key}={node_name}")
                await set_photo_classification(db, photo, facet_key, node)

            imported += 1

        await db.commit()
    return imported, skipped


def parse_args():
    parser = argparse.ArgumentParser(description="Import a competition upload manifest into the production database.")
    parser.add_argument("--manifest", required=True, help="Path to manifest JSON")
    parser.add_argument("--uploader-id", default=None, help="Uploader user UUID")
    parser.add_argument("--uploader-student-id", default=None, help="Uploader student_id")
    parser.add_argument("--approved", action="store_true", help="Mark imported photos as approved")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise RuntimeError(f"Manifest not found: {manifest_path}")

    import asyncio

    async def runner() -> int:
        uploader_id = await resolve_uploader_id(
            uploader_id=args.uploader_id,
            uploader_student_id=args.uploader_student_id,
        )
        imported, skipped = await import_manifest(
            manifest_path,
            uploader_id=uploader_id,
            approved=args.approved,
        )
        print(f"Manifest:    {manifest_path}")
        print(f"Uploader ID: {uploader_id}")
        print(f"Imported:    {imported}")
        print(f"Skipped:     {skipped}")
        return 0

    return asyncio.run(runner())


if __name__ == "__main__":
    raise SystemExit(main())
