#!/usr/bin/env python3
"""
Batch re-tagging script: re-analyze photos with V5 prompt.

Targets photos with low-quality tags or no tags, and re-runs AI analysis
with the improved V5 prompt.

Usage:
    python scripts/retag_photos.py --dry-run                  # Preview what would be re-tagged
    python scripts/retag_photos.py --limit 10                 # Re-tag 10 photos
    python scripts/retag_photos.py --all                      # Re-tag all photos
    python scripts/retag_photos.py --photo-id <uuid>          # Re-tag specific photo
    python scripts/retag_photos.py --low-quality              # Only re-tag low quality
"""
import asyncio
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import engine, AsyncSessionLocal
from app.services.ai_tasks import run_ai_analysis_task, create_ai_analysis_task, apply_ai_analysis_task
from app.services.runtime_settings import get_runtime_settings
from app.services.tag_validation import validate_analysis_result
from sqlalchemy import text


async def find_photos_to_retag(
    limit: int = 100,
    low_quality_only: bool = False,
    photo_id: str | None = None,
) -> list[dict]:
    """Find photos that need re-tagging."""
    async with engine.begin() as conn:
        if photo_id:
            result = await conn.execute(
                text("SELECT id, filename, description FROM photos WHERE id = :pid"),
                {"pid": photo_id}
            )
            rows = result.fetchall()
            return [{"id": r[0], "filename": r[1], "description": r[2]} for r in rows]

        if low_quality_only:
            # Find photos with few tags or tags that are too generic
            result = await conn.execute(text(f"""
                SELECT p.id, p.filename, p.description, COUNT(pt.tag_id) as tag_count
                FROM photos p
                LEFT JOIN photo_tags pt ON pt.photo_id = p.id
                GROUP BY p.id, p.filename, p.description
                HAVING COUNT(pt.tag_id) < 5
                ORDER BY COUNT(pt.tag_id) ASC
                LIMIT {limit}
            """))
        else:
            # Find all photos, prioritizing those without tags
            result = await conn.execute(text(f"""
                SELECT p.id, p.filename, p.description, COUNT(pt.tag_id) as tag_count
                FROM photos p
                LEFT JOIN photo_tags pt ON pt.photo_id = p.id
                GROUP BY p.id, p.filename, p.description
                ORDER BY COUNT(pt.tag_id) ASC, p.id
                LIMIT {limit}
            """))

        rows = result.fetchall()
        return [{"id": r[0], "filename": r[1], "description": r[2], "tag_count": r[3]} for r in rows]


async def retag_photo(photo_id: str, dry_run: bool = False) -> dict:
    """Re-tag a single photo using V5 prompt."""
    async with AsyncSessionLocal() as db:
        from app.crud import photo as photo_crud
        photo = await photo_crud.get_photo(db, photo_id)
        if not photo:
            return {"photo_id": photo_id, "status": "error", "message": "Photo not found"}

        runtime_settings = await get_runtime_settings(db)
        if not runtime_settings.ai_enabled:
            return {"photo_id": photo_id, "status": "error", "message": "AI disabled"}

        # Get provider info
        if not runtime_settings.providers:
            return {"photo_id": photo_id, "status": "error", "message": "No AI providers"}

        provider = runtime_settings.providers[0]

    if dry_run:
        return {"photo_id": photo_id, "status": "dry_run", "filename": photo.filename}

    # Create and run analysis task
    async with AsyncSessionLocal() as db:
        task = await create_ai_analysis_task(
            db=db,
            photo=photo,
            requested_by_id=None,
            provider=provider.provider_type,
            model_id=provider.model_id,
        )
        task_id = task.id

    # Run analysis (outside of session to avoid long-lived connections)
    task_result = await run_ai_analysis_task(task_id)

    if task_result is None or task_result.status == "failed":
        return {
            "photo_id": photo_id,
            "status": "failed",
            "error": task_result.error_message if task_result else "Unknown error",
        }

    # Apply result
    async with AsyncSessionLocal() as db:
        from app.services.ai_tasks import get_ai_task
        task = await get_ai_task(db, task_id)
        if task and task.status == "completed":
            unresolved = await apply_ai_analysis_task(db, task, reviewer_id=None)
            tags = (task.result_json or {}).get("free_tags", [])
            return {
                "photo_id": photo_id,
                "status": "applied",
                "tags": tags,
                "unresolved": unresolved,
            }

    return {"photo_id": photo_id, "status": "completed", "message": "Task completed but not applied"}


async def main():
    parser = argparse.ArgumentParser(description="Batch re-tag photos with V5 prompt")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--limit", type=int, default=10, help="Max photos to process")
    parser.add_argument("--all", action="store_true", help="Process all photos")
    parser.add_argument("--photo-id", type=str, help="Process specific photo by ID")
    parser.add_argument("--low-quality", action="store_true", help="Only process low-quality photos (<5 tags)")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between API calls (seconds)")
    args = parser.parse_args()

    if args.all:
        args.limit = 1000

    print("=" * 60)
    print("视觉北化 V5 批量重新打标")
    print("=" * 60)
    print(f"模式: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"限制: {args.limit} 张照片")
    print()

    # Find photos
    photos = await find_photos_to_retag(
        limit=args.limit,
        low_quality_only=args.low_quality,
        photo_id=args.photo_id,
    )

    if not photos:
        print("没有找到需要重新打标的照片。")
        return

    print(f"找到 {len(photos)} 张照片需要处理:")
    for p in photos[:10]:
        tc = p.get("tag_count", "?")
        print(f"  - {p['filename'][:40]:40s} (标签数: {tc})")
    if len(photos) > 10:
        print(f"  ... 还有 {len(photos) - 10} 张")
    print()

    if args.dry_run:
        print("[DRY RUN] 以上照片将被重新打标。运行不带 --dry-run 参数来执行。")
        return

    # Process photos
    results = {"applied": 0, "failed": 0, "skipped": 0}
    for i, photo in enumerate(photos):
        print(f"[{i+1}/{len(photos)}] 处理: {photo['filename'][:40]}...", end=" ", flush=True)

        result = await retag_photo(photo["id"], dry_run=False)

        if result["status"] == "applied":
            results["applied"] += 1
            tags = result.get("tags", [])
            print(f"✅ ({len(tags)} 个标签)")
        elif result["status"] == "failed":
            results["failed"] += 1
            print(f"❌ {result.get('error', 'Unknown')[:50]}")
        else:
            results["skipped"] += 1
            print(f"⏭️ {result.get('message', 'Skipped')}")

        # Rate limiting
        if i < len(photos) - 1:
            await asyncio.sleep(args.delay)

    print()
    print("=" * 60)
    print("处理完成:")
    print(f"  ✅ 成功: {results['applied']}")
    print(f"  ❌ 失败: {results['failed']}")
    print(f"  ⏭️ 跳过: {results['skipped']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
