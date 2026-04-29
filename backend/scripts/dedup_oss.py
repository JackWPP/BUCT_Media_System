"""
Deduplicate OSS photos by content hash (ETag) and sync local SQLite database.

Usage:
    cd backend
    python scripts/dedup_oss.py --dry-run     # preview duplicates
    python scripts/dedup_oss.py               # remove duplicates
    python scripts/dedup_oss.py --cleanup-tests  # also remove test files
"""
from __future__ import annotations

import argparse
import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boto3
from botocore.client import Config as BotoConfig
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.tag import PhotoTag
from app.models.taxonomy import PhotoClassification
from app.models.ai_analysis import AIAnalysisTask


def _get_s3_client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.S3_ENDPOINT,
        aws_access_key_id=s.S3_ACCESS_KEY,
        aws_secret_access_key=s.S3_SECRET_KEY,
        region_name=s.S3_REGION,
        use_ssl=s.S3_USE_SSL,
        config=BotoConfig(signature_version="s3v4"),
    )


def list_oss_photos(client) -> list[dict]:
    """List all objects under photos/ with key, size, etag."""
    photos = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=get_settings().S3_BUCKET, Prefix="photos/"):
        for obj in page.get("Contents", []):
            photos.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "etag": obj.get("ETag", "").strip('"'),
            })
    return photos


def find_test_files(client) -> list[str]:
    """Find test/temp files in the bucket root."""
    s = get_settings()
    resp = client.list_objects_v2(Bucket=s.S3_BUCKET, Prefix="", Delimiter="/")
    test_keys = []
    for obj in resp.get("Contents", []):
        key = obj["Key"]
        # Files without a proper prefix, or with test/tmp names
        if not key.startswith("photos/") and not key.startswith("thumbnails/"):
            test_keys.append(key)
    return test_keys


def find_duplicates(photos: list[dict]) -> dict[str, list[dict]]:
    """Group photos by ETag, return groups with >1 entries."""
    by_etag = defaultdict(list)
    for p in photos:
        by_etag[p["etag"]].append(p)
    return {k: v for k, v in by_etag.items() if len(v) > 1}


def _pick_keep(group: list[dict]) -> tuple[dict, list[dict]]:
    """Pick the best copy to keep (prefer shorter name, no '副本').

    Returns (keep, remove_list).
    """
    def score(p: dict) -> int:
        s = 0
        key = p["key"]
        # Penalize "副本" (copy) in name
        if "副本" in key:
            s -= 100
        if "copy" in key.lower():
            s -= 100
        # Prefer shorter filenames
        s -= len(key)
        return s

    sorted_group = sorted(group, key=score, reverse=True)
    return sorted_group[0], sorted_group[1:]


async def remove_db_photos(original_paths: list[str], dry_run: bool) -> int:
    """Remove photos from DB by original_path. Cascade deletes tags, classifications, tasks."""
    if not original_paths:
        return 0

    async with AsyncSessionLocal() as db:
        # Find photo IDs first
        result = await db.execute(
            select(Photo.id).where(Photo.original_path.in_(original_paths))
        )
        photo_ids = [r[0] for r in result.fetchall()]

        if not photo_ids:
            return 0

        if dry_run:
            return len(photo_ids)

        # Delete cascade: tags, classifications, tasks first (or rely on cascade FK)
        await db.execute(
            delete(PhotoTag).where(PhotoTag.photo_id.in_(photo_ids))
        )
        await db.execute(
            delete(PhotoClassification).where(PhotoClassification.photo_id.in_(photo_ids))
        )
        await db.execute(
            delete(AIAnalysisTask).where(AIAnalysisTask.photo_id.in_(photo_ids))
        )
        await db.execute(
            delete(Photo).where(Photo.id.in_(photo_ids))
        )
        await db.commit()

    return len(photo_ids)


async def run_dedup(dry_run: bool = False, cleanup_tests: bool = False):
    client = _get_s3_client()
    s = get_settings()
    bucket = s.S3_BUCKET

    actions = []

    # ── Step 1: Test files ──
    if cleanup_tests:
        test_keys = find_test_files(client)
        for k in test_keys:
            actions.append(("delete_oss_test", k, None))
        if not test_keys:
            print("No test files found.")

    # ── Step 2: Duplicate detection ──
    photos = list_oss_photos(client)
    print(f"Photos in OSS: {len(photos)}")

    dupes = find_duplicates(photos)
    if dupes:
        print(f"\nDuplicate groups found: {len(dupes)}")
        for etag, group in dupes.items():
            keep, remove_list = _pick_keep(group)
            print(f"\n  ETag: {etag[:16]}... ({group[0]['size']} bytes)")
            print(f"  KEEP:  {keep['key']}")
            for r in remove_list:
                print(f"  DEL:   {r['key']}")
                actions.append(("delete_oss_photo", r["key"], r["size"]))
    else:
        print("No duplicate photos found.")

    # ── Step 3: Execute ──
    if not actions:
        print("\nNothing to do.")
        return

    oss_delete_keys = [a[1] for a in actions if a[0].startswith("delete_oss")]
    db_delete_paths = [a[1] for a in actions if a[0] == "delete_oss_photo"]

    if dry_run:
        print(f"\n=== DRY RUN — would perform {len(actions)} actions ===")
        total_size = sum(a[2] for a in actions if a[2])
        print(f"  OSS objects to delete: {len(oss_delete_keys)} ({total_size} bytes)")
        print(f"  DB records to remove: {len(db_delete_paths)}")
        if db_delete_paths:
            removed = await remove_db_photos(db_delete_paths, dry_run=True)
            print(f"  DB cascade records: ~{removed} photos + tags + classifications")
        return

    print(f"\n=== Executing {len(actions)} actions ===")

    # Delete from OSS
    for key in oss_delete_keys:
        client.delete_object(Bucket=bucket, Key=key)
        print(f"  OSS deleted: {key}")

    # Delete from DB
    if db_delete_paths:
        removed = await remove_db_photos(db_delete_paths, dry_run=False)
        print(f"  DB removed: {removed} photos (cascade)")

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(description="OSS deduplication and cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Preview without deleting")
    parser.add_argument("--cleanup-tests", action="store_true", help="Remove test/tmp files from OSS")
    args = parser.parse_args()

    import asyncio
    asyncio.run(run_dedup(dry_run=args.dry_run, cleanup_tests=args.cleanup_tests))
    return 0


if __name__ == "__main__":
    sys.exit(main())
