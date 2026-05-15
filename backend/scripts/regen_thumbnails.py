"""
Batch migration: regenerate all thumbnails with 3:2 center crop (≤1MB)
and backfill width/height from original images.

Usage:
    python scripts/regen_thumbnails.py --dry-run   # preview only
    python scripts/regen_thumbnails.py              # execute
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.services.image_processing import create_thumbnail
import psycopg2

settings = get_settings()

import boto3
from botocore.client import Config as BotoConfig

s3 = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    region_name=settings.S3_REGION,
    use_ssl=settings.S3_USE_SSL,
    config=BotoConfig(signature_version="s3v4"),
)
BUCKET = settings.S3_BUCKET


def get_conn():
    url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    return psycopg2.connect(url)


def get_all_photos():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, filename, original_path, thumb_path
        FROM photos
        WHERE status = 'approved'
        ORDER BY created_at
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'id': r[0], 'filename': r[1], 'original_path': r[2], 'thumb_path': r[3]} for r in rows]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    photos = get_all_photos()
    print(f"Found {len(photos)} photos to process")

    if args.dry_run:
        print("Dry run complete. Run without --dry-run to execute.")
        return

    success = 0
    failed = 0
    for i, p in enumerate(photos):
        photo_id = p['id']
        original_key = p['original_path']
        thumb_key = f"thumbnails/{photo_id}_thumb.jpg"

        print(f"[{i+1}/{len(photos)}] {p['filename'][:45]:<45s} ", end="", flush=True)

        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_orig:
                tmp_orig_path = tmp_orig.name
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_thumb:
                tmp_thumb_path = tmp_thumb.name

            # Download original
            s3.download_file(BUCKET, original_key, tmp_orig_path)

            # Get original dimensions
            from PIL import Image
            with Image.open(tmp_orig_path) as img:
                orig_w, orig_h = img.size

            # Generate 3:2 thumbnail
            create_thumbnail(tmp_orig_path, tmp_thumb_path)
            thumb_size = os.path.getsize(tmp_thumb_path)

            # Upload new thumbnail (overwrite)
            s3.upload_file(tmp_thumb_path, BUCKET, thumb_key)

            # Update DB: thumb_path + width/height
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                UPDATE photos
                SET thumb_path = %s, width = %s, height = %s, updated_at = NOW()
                WHERE id = %s
            """, (thumb_key, orig_w, orig_h, photo_id))
            conn.commit()
            cur.close()
            conn.close()

            print(f"OK → {orig_w}x{orig_h}, thumb {thumb_size/1024:.0f}KB")
            success += 1

        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

        finally:
            for path in (tmp_orig_path, tmp_thumb_path):
                if 'path' in dir() and os.path.exists(path):
                    os.remove(path)

    print(f"\nDone: {success} processed, {failed} failed out of {len(photos)} total")


if __name__ == "__main__":
    main()
