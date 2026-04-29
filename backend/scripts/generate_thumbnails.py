"""
Generate thumbnails for all OSS photos and upload them back to OSS.

Thumbnails are generated locally (download via boto3 GET, which works through VPN),
then uploaded via SSH + mc pipe (PUT is blocked through VPN firewall).

Thumbnail spec: longest side 400px, JPEG quality 85, stored at:
  thumbnails/{photo_id}_thumb.jpg

Usage:
    cd backend
    python scripts/generate_thumbnails.py --dry-run     # preview
    python scripts/generate_thumbnails.py                # generate all
    python scripts/generate_thumbnails.py --limit 10     # first 10
    python scripts/generate_thumbnails.py --size 300     # custom size
"""
from __future__ import annotations

import argparse
import io
import os
import signal
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boto3
from botocore.client import Config as BotoConfig
from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.photo import Photo

try:
    from PIL import Image
except ImportError:
    print("Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

try:
    from tqdm import tqdm
    TQDM = True
except ImportError:
    TQDM = False


# ── Config ──
SSH_HOST = "121.195.148.85"
SSH_USER = "yanp"


# Global flag for graceful pause
_paused = False


def _handle_sigint(signum, frame):
    global _paused
    if not _paused:
        print("\n[PAUSE] Completing current photo... (Ctrl+C again to abort)")
        _paused = True
    else:
        print("\n[ABORT] Exiting immediately.")
        sys.exit(1)


signal.signal(signal.SIGINT, _handle_sigint)


def get_s3_client():
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


def generate_thumbnail_bytes(image_data: bytes, max_side: int, quality: int) -> tuple[bytes, int, int]:
    """Generate a JPEG thumbnail, returns (bytes, width, height)."""
    img = Image.open(io.BytesIO(image_data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) <= max_side:
        img_resized = img
    else:
        ratio = max_side / max(w, h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img_resized.save(buf, format="JPEG", quality=quality)
    return buf.getvalue(), img_resized.width, img_resized.height


def upload_thumbnail(thumb_bytes: bytes, thumb_key: str) -> None:
    """Upload thumbnail to MinIO via SSH + mc pipe (bypasses VPN write block)."""
    cmd = f"mc pipe local/buctmedia/{thumb_key}"
    proc = subprocess.run(
        ["ssh", f"{SSH_USER}@{SSH_HOST}", cmd],
        input=thumb_bytes,
        capture_output=True,
        timeout=60,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"mc pipe failed: {stderr}")


async def generate_thumbnails(
    *,
    limit: int | None = None,
    max_side: int = 400,
    quality: int = 85,
    dry_run: bool = False,
):
    s = get_settings()
    client = get_s3_client()
    bucket = s.S3_BUCKET

    async with AsyncSessionLocal() as db:
        query = (
            select(Photo)
            .where(Photo.original_path.isnot(None))
            .where(Photo.thumb_path.is_(None))
            .order_by(Photo.created_at.asc())
        )
        if limit:
            query = query.limit(limit)
        result = await db.execute(query)
        photos = list(result.scalars().all())

    if not photos:
        print("All photos already have thumbnails.")
        return

    print(f"Photos to process: {len(photos)}")
    if dry_run:
        print("=== DRY RUN — no thumbnails will be generated ===")
        return

    stats = {"done": 0, "errors": 0, "skipped": 0}
    errors = []

    it = tqdm(photos, desc="Generating thumbnails", unit="photo") if TQDM else photos
    for photo in it:
        global _paused
        if _paused:
            print(f"\nPaused at {photo.original_path}. Run again to resume.")
            break

        try:
            # Download original from OSS (GET works through VPN)
            response = client.get_object(Bucket=bucket, Key=photo.original_path)
            image_data = response["Body"].read()

            # Generate thumbnail locally
            thumb_bytes, tw, th = generate_thumbnail_bytes(image_data, max_side, quality)

            # Upload via SSH + mc pipe
            thumb_key = f"thumbnails/{photo.id}_thumb.jpg"
            upload_thumbnail(thumb_bytes, thumb_key)

            # Update DB
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Photo)
                    .where(Photo.id == photo.id)
                    .values(thumb_path=thumb_key)
                )
                await db.commit()

            stats["done"] += 1

        except Exception as exc:
            stats["errors"] += 1
            errors.append((photo.id[:8], photo.original_path, str(exc)))
            if TQDM:
                tqdm.write(f"  ERROR {photo.original_path}: {exc}")

    print(f"\nDone: {stats['done']} thumbnails")
    print(f"Errors: {stats['errors']}")
    if errors:
        print("\nErrors detail:")
        for pid, path, msg in errors[:10]:
            print(f"  {pid} {path}: {msg}")


def main():
    parser = argparse.ArgumentParser(description="Generate thumbnails for OSS photos")
    parser.add_argument("--limit", type=int, default=None, help="Max photos to process")
    parser.add_argument("--size", type=int, default=400, help="Max side length in px (default: 400)")
    parser.add_argument("--quality", type=int, default=85, help="JPEG quality 1-100 (default: 85)")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no generation")
    args = parser.parse_args()

    import asyncio
    asyncio.run(generate_thumbnails(
        limit=args.limit,
        max_side=args.size,
        quality=args.quality,
        dry_run=args.dry_run,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
