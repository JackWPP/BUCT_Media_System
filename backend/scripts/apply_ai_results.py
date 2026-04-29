"""
Apply pending AI analysis results to photos (classifications + tags).

Usage:
    cd backend
    python scripts/apply_ai_results.py                        # apply all completed
    python scripts/apply_ai_results.py --dry-run              # preview only
    python scripts/apply_ai_results.py --limit 10             # apply first 10
"""
import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_analysis import AIAnalysisTask
from app.models.user import User
from app.services.ai_tasks import apply_ai_analysis_task

try:
    from tqdm import tqdm
    TQDM = True
except ImportError:
    TQDM = False


async def _find_admin_id() -> str | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User.id).where(User.role == "admin").limit(1))
        row = result.scalar_one_or_none()
        return row


async def apply_all(limit: int | None = None, dry_run: bool = False):
    admin_id = await _find_admin_id()
    if not admin_id:
        print("[ERROR] No admin user found.")
        return

    async with AsyncSessionLocal() as db:
        query = select(AIAnalysisTask).where(
            AIAnalysisTask.status == "completed",
            AIAnalysisTask.result_json.isnot(None),
        ).order_by(AIAnalysisTask.created_at.asc())
        if limit:
            query = query.limit(limit)
        result = await db.execute(query)
        tasks = list(result.scalars().all())

    if not tasks:
        print("No completed AI tasks to apply.")
        return

    if dry_run:
        print(f"Would apply {len(tasks)} AI results (dry-run)")
        return

    print(f"Applying AI results for {len(tasks)} photos...")

    stats = {"applied": 0, "errors": 0, "total_tags": 0, "total_classifications": 0}
    errors = []

    it = tqdm(tasks, desc="Applying", unit="task") if TQDM else tasks
    for task in it:
        try:
            async with AsyncSessionLocal() as db:
                task_obj = await db.get(AIAnalysisTask, task.id)
                if task_obj is None or task_obj.status != "completed":
                    continue
                unresolved = await apply_ai_analysis_task(db, task_obj, admin_id)
                stats["applied"] += 1
                if task_obj.result_json:
                    import json
                    r = json.loads(task_obj.result_json) if isinstance(task_obj.result_json, str) else task_obj.result_json
                    n_tags = len(r.get("free_tags", []))
                    n_cls = len([v for v in (r.get("classifications") or {}).values() if v and v != "null"])
                    stats["total_tags"] += n_tags
                    stats["total_classifications"] += n_cls
                if unresolved:
                    errors.append((task.photo_id, unresolved))
        except Exception as exc:
            stats["errors"] += 1
            errors.append((task.photo_id, str(exc)))

    print(f"\nApplied: {stats['applied']}")
    print(f"Errors:  {stats['errors']}")
    print(f"Tags written: ~{stats['total_tags']}")
    print(f"Classifications written: ~{stats['total_classifications']}")
    if errors:
        print(f"\nIssues ({len(errors)}):")
        for pid, msg in errors[:10]:
            print(f"  {pid[:20]}: {msg}")


def main():
    parser = argparse.ArgumentParser(description="Apply pending AI analysis results to photos")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(apply_all(limit=args.limit, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
