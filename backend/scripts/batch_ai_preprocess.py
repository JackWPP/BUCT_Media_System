"""
Batch AI preprocessing CLI using local Qwen3-VL model.

Features:
  - Resume from interruption (checkpoint-based)
  - Pause: Ctrl+C once = pause after current photo; twice = force quit
  - Pause file: touch .batch_ai_pause in backend/ to pause gracefully
  - Progress bar with ETA, rate, per-photo timing

Usage:
    cd backend
    python scripts/batch_ai_preprocess.py                        # process all pending
    python scripts/batch_ai_preprocess.py --limit 10             # test with 10 photos
    python scripts/batch_ai_preprocess.py --limit 10 --apply     # test + auto-apply
    python scripts/batch_ai_preprocess.py --resume               # resume from checkpoint
    python scripts/batch_ai_preprocess.py --dry-run              # count only
    python scripts/batch_ai_preprocess.py --status failed --retry # retry failed
    python scripts/batch_ai_preprocess.py --clean                # clear checkpoint
"""
import argparse
import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, func, and_, update
from app.core.database import AsyncSessionLocal
from app.models.photo import Photo
from app.models.ai_analysis import AIAnalysisTask
from app.services.ai_tasks import run_ai_analysis_task, apply_ai_analysis_task, create_ai_analysis_task
from app.services.runtime_settings import get_runtime_settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CHECKPOINT_FILE = Path(__file__).parent.parent / ".batch_ai_checkpoint.json"
PAUSE_FILE = Path(__file__).parent.parent / ".batch_ai_pause"

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# ---------------------------------------------------------------------------
# Global state for signal handling
# ---------------------------------------------------------------------------
_shutdown_requested = False
_force_quit = False
_first_sigint_time = 0.0


def _signal_handler(signum, frame):
    global _shutdown_requested, _force_quit, _first_sigint_time
    now = time.time()
    if _shutdown_requested and (now - _first_sigint_time < 2):
        _force_quit = True
        print("\n[FORCE QUIT] Terminating immediately...")
        os._exit(1)
    _shutdown_requested = True
    _first_sigint_time = now
    print("\n[PAUSE] Finishing current photo, then saving checkpoint...")
    print("  Press Ctrl+C again within 2s to force quit.")


signal.signal(signal.SIGINT, _signal_handler)

# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        try:
            return json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"processed_ids": [], "stats": {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0},
            "failed_photos": [], "started_at": None}


def _save_checkpoint(state: dict) -> None:
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    CHECKPOINT_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _clear_checkpoint() -> None:
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


def _clear_pause_file() -> None:
    if PAUSE_FILE.exists():
        PAUSE_FILE.unlink()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _find_admin_id() -> str | None:
    from app.models.user import User
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User.id).where(User.role == "admin").limit(1))
        row = result.scalar_one_or_none()
        return row


async def _count_eligible(status_filter: str, retry: bool, processed_ids: set[str]) -> int:
    """Count photos still needing AI processing, excluding already-processed in checkpoint."""
    async with AsyncSessionLocal() as db:
        conditions = [
            Photo.original_path.isnot(None),
            Photo.original_path != "",
            Photo.processing_status == status_filter,
        ]
        if processed_ids and not retry:
            conditions.append(Photo.id.notin_(processed_ids))
        result = await db.execute(
            select(func.count(Photo.id)).where(and_(*conditions))
        )
        return result.scalar() or 0


async def _get_eligible_photos(
    status_filter: str, limit: int | None, processed_ids: set[str], retry: bool
):
    """Get photos needing AI processing, excluding completed ones."""
    async with AsyncSessionLocal() as db:
        conditions = [
            Photo.original_path.isnot(None),
            Photo.original_path != "",
            Photo.processing_status == status_filter,
        ]
        if processed_ids and not retry:
            conditions.append(Photo.id.notin_(processed_ids))
        query = select(Photo).where(and_(*conditions)).order_by(Photo.created_at.asc())
        if limit is not None:
            query = query.limit(limit)
        result = await db.execute(query)
        return result.scalars().all()


async def _has_completed_task(photo_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.count(AIAnalysisTask.id)).where(
                and_(
                    AIAnalysisTask.photo_id == photo_id,
                    AIAnalysisTask.status.in_(["completed", "applied"]),
                )
            )
        )
        return (result.scalar() or 0) > 0


async def _cleanup_stuck_tasks(photo_id: str) -> None:
    """Remove stuck pending/processing tasks for a photo (leftover from crashes)."""
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(AIAnalysisTask)
            .where(
                and_(
                    AIAnalysisTask.photo_id == photo_id,
                    AIAnalysisTask.status.in_(["pending", "processing"]),
                )
            )
            .values(status="failed", error_message="Cleaned up by batch processor restart",
                    updated_at=datetime.utcnow())
        )
        await db.commit()


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m{s:02d}s"
    h, r = divmod(int(seconds), 3600)
    m, s = divmod(r, 60)
    return f"{h}h{m:02d}m{s:02d}s"


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

async def process_batch(
    limit: int | None = None,
    apply: bool = False,
    status_filter: str = "pending",
    retry: bool = False,
    dry_run: bool = False,
    resume: bool = False,
    admin_id: str | None = None,
) -> dict:
    global _shutdown_requested

    # Resolve admin
    if not admin_id:
        admin_id = await _find_admin_id()
    if not admin_id:
        print("[ERROR] No admin user found. Register an admin user first.")
        return {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    # Load checkpoint
    checkpoint = _load_checkpoint() if resume else {"processed_ids": [], "stats": {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}, "failed_photos": [], "started_at": None}
    processed_ids = set(checkpoint.get("processed_ids", [])) if resume else set()
    saved_stats = checkpoint.get("stats", {}) if resume else {}
    failed_photos: list[tuple[str, str]] = checkpoint.get("failed_photos", []) if resume else []

    # Count eligible
    total = await _count_eligible(status_filter, retry, processed_ids)
    previously_done = saved_stats.get("processed", 0)

    if dry_run:
        print(f"  Photos with processing_status='{status_filter}': {total}")
        if resume and previously_done:
            print(f"  Previously processed (in checkpoint): {previously_done}")
        return {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0, "total": total}

    if total == 0:
        if resume and previously_done:
            print(f"All {previously_done} photos already processed. Nothing left to do.")
            _clear_checkpoint()
        else:
            print(f"No photos with processing_status='{status_filter}' found.")
        return {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    # Runtime settings
    async with AsyncSessionLocal() as db:
        runtime = await get_runtime_settings(db)
        provider_info = runtime.default_provider
        model_name = provider_info.model_id if provider_info else "unknown"
        provider_type = provider_info.provider_type if provider_info else "unknown"

    if not runtime.ai_enabled:
        print("[ERROR] AI is disabled. Enable it via admin settings or .env")
        return {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    # Header
    print(f"Model:      {model_name}")
    print(f"Provider:   {provider_type}")
    print(f"Auto-apply: {apply}")
    if resume and previously_done:
        print(f"Resuming:   {previously_done} already done, {total} remaining")
    else:
        print(f"To process: {total}")
    print(f"Pause:      Ctrl+C (save & exit)  |  touch .batch_ai_pause to pause")
    print(f"{'=' * 60}")

    # Clear stale pause file from previous run
    _clear_pause_file()

    # Stats (accumulate with checkpoint if resuming)
    stats = {
        "processed": saved_stats.get("processed", 0),
        "succeeded": saved_stats.get("succeeded", 0),
        "failed": saved_stats.get("failed", 0),
        "skipped": saved_stats.get("skipped", 0),
    }

    photos = await _get_eligible_photos(status_filter, limit, processed_ids, retry)
    target_count = len(photos)
    start_time = time.time()
    per_photo_times: list[float] = []

    # Setup progress bar
    pbar = None
    if TQDM_AVAILABLE and target_count > 0:
        pbar = tqdm(
            total=target_count,
            desc="Processing",
            unit="photo",
            ncols=120,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}",
        )
        pbar.set_postfix_str(f"ok={stats['succeeded']} fail={stats['failed']}")

    try:
        for i, photo in enumerate(photos):
            # Check for pause file
            if PAUSE_FILE.exists():
                print(f"\n[PAUSE] Pause file detected. Saving checkpoint after {stats['processed']} photos...")
                _shutdown_requested = True

            # Handle shutdown / pause
            if _shutdown_requested:
                remaining_ids = {p.id for p in photos[i:]}
                checkpoint_state = {
                    "processed_ids": list(processed_ids),
                    "stats": stats,
                    "failed_photos": failed_photos,
                    "started_at": checkpoint.get("started_at") or datetime.now(timezone.utc).isoformat(),
                    "remaining_count": len(remaining_ids),
                }
                _save_checkpoint(checkpoint_state)
                _clear_pause_file()
                if pbar:
                    pbar.close()
                print(f"\n[PAUSED] Checkpoint saved: {CHECKPOINT_FILE}")
                print(f"  Processed: {stats['processed']} | Remaining: ~{len(remaining_ids)}")
                print(f"  Resume with: python scripts/batch_ai_preprocess.py --resume")
                return stats

            # Skip completed (DB check — handles resumes without checkpoint too)
            if not retry:
                has_task = await _has_completed_task(photo.id)
                if has_task:
                    stats["skipped"] += 1
                    processed_ids.add(photo.id)
                    if pbar:
                        pbar.update(1)
                        pbar.set_postfix_str(f"ok={stats['succeeded']} fail={stats['failed']} skip={stats['skipped']}")
                    continue

            # Clean up any stuck tasks from previous runs
            await _cleanup_stuck_tasks(photo.id)

            # Create and run AI task
            photo_start = time.time()
            async with AsyncSessionLocal() as db:
                task = await create_ai_analysis_task(
                    db, photo=photo, requested_by_id=admin_id,
                    provider=runtime.ai_provider, model_id=runtime.ai_model_id,
                )

            task_result = await run_ai_analysis_task(task.id)
            photo_time = time.time() - photo_start
            per_photo_times.append(photo_time)
            stats["processed"] += 1
            processed_ids.add(photo.id)

            if task_result and task_result.status == "completed":
                stats["succeeded"] += 1
                if apply:
                    async with AsyncSessionLocal() as db:
                        task_obj = await db.get(AIAnalysisTask, task.id)
                        if task_obj and task_obj.status == "completed":
                            try:
                                await apply_ai_analysis_task(db, task_obj, admin_id)
                            except Exception as exc:
                                tqdm.write(f"  [WARN] Apply failed for {photo.filename}: {exc}")
            else:
                stats["failed"] += 1
                error_msg = task_result.error_message if task_result else "Unknown"
                failed_photos.append((photo.filename or photo.id, error_msg))

            # Update progress bar
            avg_time = sum(per_photo_times[-10:]) / len(per_photo_times[-10:]) if per_photo_times else photo_time
            if pbar:
                pbar.update(1)
                pbar.set_postfix_str(
                    f"ok={stats['succeeded']} fail={stats['failed']} "
                    f"last={photo_time:.1f}s avg={avg_time:.1f}s"
                )
            else:
                etas = (target_count - i - 1) * avg_time
                print(f"  [{i+1}/{target_count}] {photo.filename[:40]:<40} "
                      f"ok={stats['succeeded']} fail={stats['failed']} "
                      f"{photo_time:.1f}s ETA={_format_duration(etas)}")

            # Save incremental checkpoint every 10 photos
            if stats["processed"] % 10 == 0:
                remaining_ids = {p.id for p in photos[i+1:]}
                checkpoint_state = {
                    "processed_ids": list(processed_ids),
                    "stats": stats,
                    "failed_photos": failed_photos,
                    "started_at": checkpoint.get("started_at") or datetime.now(timezone.utc).isoformat(),
                    "remaining_count": len(remaining_ids),
                }
                _save_checkpoint(checkpoint_state)

    except KeyboardInterrupt:
        _shutdown_requested = True
        if pbar:
            pbar.close()
        remaining_ids = {p.id for p in photos[stats['processed'] - stats['skipped']:]} if stats['processed'] > 0 else set()
        checkpoint_state = {
            "processed_ids": list(processed_ids),
            "stats": stats,
            "failed_photos": failed_photos,
            "started_at": checkpoint.get("started_at") or datetime.now(timezone.utc).isoformat(),
            "remaining_count": len(remaining_ids),
        }
        _save_checkpoint(checkpoint_state)
        print(f"\n[PAUSED] Checkpoint saved. Resume with: python scripts/batch_ai_preprocess.py --resume")
        return stats
    finally:
        if pbar:
            pbar.close()

    # Done — clear checkpoint
    _clear_checkpoint()
    _clear_pause_file()

    elapsed = time.time() - start_time
    avg = sum(per_photo_times) / len(per_photo_times) if per_photo_times else 0

    print(f"\n{'=' * 60}")
    print(f"Results")
    print(f"{'=' * 60}")
    print(f"  Processed:{stats['processed']:>6}")
    print(f"  Succeeded:{stats['succeeded']:>6}")
    print(f"  Failed:   {stats['failed']:>6}")
    print(f"  Skipped:  {stats['skipped']:>6}")
    print(f"  Duration: {_format_duration(elapsed):>6}")
    print(f"  Avg time: {avg:.1f}s/photo")
    if per_photo_times:
        print(f"  Fastest:  {min(per_photo_times):.1f}s")
        print(f"  Slowest:  {max(per_photo_times):.1f}s")

    if failed_photos:
        print(f"\nFailed photos ({len(failed_photos)}):")
        for name, err in failed_photos[:10]:
            print(f"  - {name[:50]}: {err[:80]}")
        if len(failed_photos) > 10:
            print(f"  ... and {len(failed_photos) - 10} more")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Batch AI preprocessing for BUCT Media photos (Qwen3-VL)"
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Max number of photos to process")
    parser.add_argument("--apply", action="store_true",
                        help="Auto-apply AI results to photos after analysis")
    parser.add_argument("--status", type=str, default="pending",
                        help="Filter by processing_status (default: pending)")
    parser.add_argument("--retry", action="store_true",
                        help="Reprocess photos that already have completed tasks")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count eligible photos only, no processing")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last checkpoint")
    parser.add_argument("--clean", action="store_true",
                        help="Clear checkpoint file and exit")
    parser.add_argument("--admin-id", type=str, default=None,
                        help="UUID of admin user (auto-detected)")
    args = parser.parse_args()

    if args.clean:
        _clear_checkpoint()
        _clear_pause_file()
        print("Checkpoint cleared.")
        return 0

    if not TQDM_AVAILABLE:
        print("[NOTE] Install tqdm for progress bars: pip install tqdm\n")

    stats = asyncio.run(process_batch(
        limit=args.limit,
        apply=args.apply,
        status_filter=args.status,
        retry=args.retry,
        dry_run=args.dry_run,
        resume=args.resume,
        admin_id=args.admin_id,
    ))

    return 0 if stats.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
