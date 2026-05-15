"""
Batch migration: generate compressed versions (≤5MB) for existing photos.

Usage:
    python scripts/generate_compressed.py --dry-run   # preview only
    python scripts/generate_compressed.py              # execute
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.services.image_processing import create_compressed
import psycopg2

settings = get_settings()

# S3 client
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
    """Get a psycopg2 connection from DATABASE_URL."""
    url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    return psycopg2.connect(url)


def get_candidates():
    """Find photos > 5MB without compressed_path."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, filename, original_path, file_size
        FROM photos
        WHERE status = 'approved'
          AND file_size > 5242880
          AND compressed_path IS NULL
        ORDER BY file_size DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    # Return as list of dicts for consistent access
    return [type('Row', (), {'id': r[0], 'filename': r[1], 'original_path': r[2], 'file_size': r[3]})() for r in rows]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    candidates = get_candidates()
    print(f"Found {len(candidates)} photos to compress (> 5MB, no compressed_path)")

    if args.dry_run:
        for row in candidates:
            size_mb = row.file_size / 1048576
            print(f"  {row.id[:12]}... {row.filename[:40]:<40s} {size_mb:.1f}MB")
        print("\nDry run complete. Run without --dry-run to execute.")
        return

    success = 0
    failed = 0
    for i, row in enumerate(candidates):
        photo_id = row.id
        original_key = row.original_path
        size_mb = row.file_size / 1048576
        print(f"[{i+1}/{len(candidates)}] {row.filename[:40]} ({size_mb:.1f}MB) ... ", end="", flush=True)

        compressed_key = f"compressed/{photo_id}_compressed.jpg"

        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_orig:
                tmp_orig_path = tmp_orig.name

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_comp:
                tmp_comp_path = tmp_comp.name

            # Download original
            s3.download_file(BUCKET, original_key, tmp_orig_path)

            # Compress
            _, comp_w, comp_h, comp_size = create_compressed(tmp_orig_path, tmp_comp_path)
            comp_mb = comp_size / 1048576

            # Upload compressed
            s3.upload_file(tmp_comp_path, BUCKET, compressed_key)

            # Update DB
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "UPDATE photos SET compressed_path = %s, updated_at = NOW() WHERE id = %s",
                (compressed_key, photo_id)
            )
            conn.commit()
            cur.close()
            conn.close()

            print(f"OK → {comp_w}x{comp_h}, {comp_mb:.1f}MB")
            success += 1

        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

        finally:
            for p in (tmp_orig_path, tmp_comp_path):
                if os.path.exists(p):
                    os.remove(p)

    print(f"\nDone: {success} compressed, {failed} failed out of {len(candidates)} total")


if __name__ == "__main__":
    main()
