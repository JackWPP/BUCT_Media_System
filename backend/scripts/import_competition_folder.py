from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.user import User
from app.services.competition_import import (
    build_classification_values,
    build_description,
    scan_competition_directory,
)
from app.services.image_processing import process_uploaded_image
from app.services.storage import cleanup_staged_files, get_storage
from app.services.taxonomy import ensure_default_taxonomy, resolve_taxonomy_node, set_photo_classification

DEFAULT_SOURCE_DIR = Path(r"D:\BUCTuploader\第八届昌平校区摄影大赛获奖作品\1.风光类作品")
DEFAULT_GALLERY_YEAR = "2025年第八届获奖作品"
DEFAULT_PHOTO_TYPE = "建筑楼宇"

MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def get_mime_type(path: Path) -> str:
    return MIME_MAP.get(path.suffix.lower(), "application/octet-stream")


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
            result = await db.execute(
                select(User).where(User.student_id == uploader_student_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise RuntimeError(f"Uploader student_id not found: {uploader_student_id}")
            return str(user.id)

        result = await db.execute(
            select(User).where(User.role == "admin").order_by(User.created_at.asc())
        )
        user = result.scalars().first()
        if user is None:
            raise RuntimeError("No admin user found. Use --uploader-id or --uploader-student-id.")
        return str(user.id)


async def import_record(record, *, uploader_id: str, approved: bool) -> str:
    storage = get_storage()
    photo_uuid = record.photo_uuid

    async with AsyncSessionLocal() as db:
        existing = await db.get(Photo, photo_uuid)
        if existing is not None:
            return "skipped"

        await ensure_default_taxonomy(db)

        temp_dir = Path(tempfile.mkdtemp(prefix="buct-competition-import-"))
        staged_original_path = temp_dir / record.filename
        staged_thumb_path = None
        staged_compressed_path = None
        stored_media = None

        try:
            shutil.copy2(record.source_path, staged_original_path)
            processing_result = process_uploaded_image(
                str(staged_original_path),
                photo_uuid,
                output_dir=str(temp_dir),
            )
            staged_thumb_path = processing_result.get("thumb_path")
            staged_compressed_path = processing_result.get("compressed_path")
            stored_media = storage.persist_photo_files(
                photo_uuid,
                str(staged_original_path),
                staged_thumb_path,
                staged_compressed_path,
            )

            now = datetime.utcnow()
            photo = Photo(
                id=photo_uuid,
                uploader_id=uploader_id,
                filename=record.filename,
                original_path=stored_media.original_path,
                thumb_path=stored_media.thumb_path,
                compressed_path=stored_media.compressed_path,
                width=processing_result.get("width"),
                height=processing_result.get("height"),
                file_size=stored_media.file_size,
                mime_type=get_mime_type(record.source_path),
                season=None,
                category="Landscape" if record.photo_type in {"风光类", "建筑楼宇", "校区设施", "自然生态"} else "Documentary",
                campus=record.campus,
                description=build_description(record),
                exif_data=processing_result.get("exif_data", {}),
                status="approved" if approved else "pending",
                processing_status="manual",
                captured_at=processing_result.get("captured_at"),
                published_at=now if approved else None,
                created_at=now,
                updated_at=now,
                views=0,
            )
            db.add(photo)
            await db.flush()

            for facet_key, node_name in build_classification_values(record).items():
                node = await resolve_taxonomy_node(db, facet_key, node_name)
                if node is None:
                    raise RuntimeError(f"Taxonomy node not found: {facet_key}={node_name}")
                await set_photo_classification(db, photo, facet_key, node)

            await db.commit()
            return "imported"
        except Exception:
            await db.rollback()
            if stored_media is not None:
                storage.delete_file(stored_media.original_path)
                storage.delete_file(stored_media.thumb_path)
                storage.delete_file(stored_media.compressed_path)
            raise
        finally:
            cleanup_staged_files(
                str(staged_original_path),
                staged_thumb_path,
                staged_compressed_path,
            )
            shutil.rmtree(temp_dir, ignore_errors=True)


async def main_async(args) -> int:
    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        raise RuntimeError(f"Source directory not found: {source_dir}")

    records = scan_competition_directory(
        source_dir,
        photo_type=args.photo_type,
        gallery_year=args.gallery_year,
    )
    if args.limit is not None:
        records = records[: args.limit]

    if not records:
        print("No eligible image files found.")
        return 0

    uploader_id = await resolve_uploader_id(
        uploader_id=args.uploader_id,
        uploader_student_id=args.uploader_student_id,
    )

    print(f"Source dir:   {source_dir}")
    print(f"Uploader ID:  {uploader_id}")
    print(f"Photo type:   {args.photo_type}")
    print(f"Gallery year: {args.gallery_year}")
    print(f"Approved:     {args.approved}")
    print(f"Images found: {len(records)}")

    preview = records[: min(5, len(records))]
    print("\nPreview:")
    for record in preview:
        print(
            f"  - {record.relative_path.as_posix()} | "
            f"title={record.title or '-'} | author={record.author or '-'} | award={record.award_level or '-'}"
        )

    if args.dry_run:
        print("\nDry run complete. Re-run with --apply to import.")
        return 0

    stats = {"imported": 0, "skipped": 0, "failed": 0}
    failures: list[str] = []
    for index, record in enumerate(records, start=1):
        try:
            outcome = await import_record(record, uploader_id=uploader_id, approved=args.approved)
            stats[outcome] += 1
            print(f"[{index}/{len(records)}] {outcome.upper():8s} {record.relative_path.as_posix()}")
        except Exception as exc:  # noqa: BLE001
            stats["failed"] += 1
            failures.append(f"{record.relative_path.as_posix()}: {exc}")
            print(f"[{index}/{len(records)}] FAILED   {record.relative_path.as_posix()} -> {exc}")

    print("\nSummary:")
    print(f"  imported: {stats['imported']}")
    print(f"  skipped:  {stats['skipped']}")
    print(f"  failed:   {stats['failed']}")
    if failures:
        print("\nFailures:")
        for failure in failures[:20]:
            print(f"  - {failure}")
    return 1 if stats["failed"] else 0


def parse_args():
    parser = argparse.ArgumentParser(description="Import a competition folder into storage and database.")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR), help="Source folder to scan")
    parser.add_argument("--gallery-year", default=DEFAULT_GALLERY_YEAR, help="Taxonomy gallery_year node name")
    parser.add_argument("--photo-type", default=DEFAULT_PHOTO_TYPE, help="Taxonomy photo_type node name")
    parser.add_argument("--uploader-id", default=None, help="Uploader user UUID")
    parser.add_argument("--uploader-student-id", default=None, help="Uploader student_id")
    parser.add_argument("--limit", type=int, default=None, help="Import only the first N files")
    parser.add_argument("--apply", action="store_true", help="Perform upload and DB insert")
    parser.add_argument("--approved", action="store_true", help="Mark imported photos as approved and publish them")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.apply and args.dry_run:
        raise RuntimeError("--apply and --dry-run cannot be used together.")
    if not args.apply:
        args.dry_run = True
    import asyncio

    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
