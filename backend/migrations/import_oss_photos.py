"""
Import OSS photos from the BUCTuploader project into the main database.

Reads scenery_index.db and creates Photo records for photos already uploaded
to MinIO S3. Uses UUIDv5 for deterministic, idempotent photo IDs.

Usage:
    cd backend
    python migrations/import_oss_photos.py                        # preview mode
    python migrations/import_oss_photos.py --apply                 # apply changes
    python migrations/import_oss_photos.py --dry-run --limit 10    # preview first 10
    python migrations/import_oss_photos.py --apply --uploader-id <UUID>
"""
import argparse
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Deterministic namespace for UUIDv5 generation
OSS_IMPORT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

DB_PATH = "visual_buct.db"
UPLOADER_DB_PATH = os.environ.get(
    "UPLOADER_DB_PATH",
    r"D:\BUCTuploader\scenery_index.db",
)

# Category mapping: uploader Chinese -> main system English
CATEGORY_MAP = {
    "风光类": "Landscape",
    "纪实类": "Documentary",
}

MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_deterministic_uuid(oss_key: str) -> str:
    """Generate a stable UUIDv5 from an OSS key."""
    return str(uuid.uuid5(OSS_IMPORT_NAMESPACE, oss_key))


def build_description(row: sqlite3.Row) -> str | None:
    """Build a human-readable description from metadata."""
    title = (row["title"] or "").strip()
    author = (row["author"] or "").strip()
    author_role = (row["author_role"] or "").strip()
    rank = (row["rank"] or "").strip()
    score = row["score"]
    year = row["year"]
    edition = row["edition"]
    category = row["category"]
    entry_number = row["entry_number"]

    if title and author:
        base = f"{title} - {author}"
        if author_role:
            base += f"（{author_role}）"
        if rank:
            base += f" | 排名: {rank}"
        if score is not None:
            base += f" | 评分: {score}"
        return base

    if title:
        base = title
        if rank:
            base += f" | 排名: {rank}"
        if score is not None:
            base += f" | 评分: {score}"
        return base

    desc = f"{year}年昌平校区摄影大赛{edition} {category}"
    if entry_number is not None:
        desc += f" #{entry_number}"
    return desc


def get_mime_type(file_ext: str) -> str:
    """Map file extension to MIME type."""
    return MIME_MAP.get((file_ext or "").lower(), "image/jpeg")


def category_to_english(category: str) -> str:
    """Map Chinese category to English."""
    return CATEGORY_MAP.get(category, "Documentary")


def parse_iso_timestamp(ts: str | None) -> str | None:
    """Parse ISO 8601 timestamp to SQLite-compatible datetime string."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return None


def find_admin_user(conn: sqlite3.Connection) -> str | None:
    """Find the first admin user in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    row = cursor.fetchone()
    return row["id"] if row else None


# ---------------------------------------------------------------------------
# Main migration logic
# ---------------------------------------------------------------------------

def import_photos(
    apply: bool = False,
    uploader_id: str | None = None,
    limit: int | None = None,
):
    # Validate uploader DB
    if not os.path.exists(UPLOADER_DB_PATH):
        print(f"[ERROR] Uploader database not found: {UPLOADER_DB_PATH}")
        print(f"  Set UPLOADER_DB_PATH environment variable to override.")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Main database not found: {DB_PATH}")
        sys.exit(1)

    # Connect to both databases
    uploader_conn = sqlite3.connect(UPLOADER_DB_PATH)
    uploader_conn.row_factory = sqlite3.Row

    main_conn = sqlite3.connect(DB_PATH)
    main_conn.row_factory = sqlite3.Row

    # Resolve uploader user ID
    if not uploader_id:
        uploader_id = find_admin_user(main_conn)
    if not uploader_id:
        print("[ERROR] No uploader_id provided and no admin user found in main database.")
        print("  Use --uploader-id to specify a user UUID.")
        uploader_conn.close()
        main_conn.close()
        sys.exit(1)

    print(f"Uploader user ID: {uploader_id}")

    # Query uploaded photos
    query = "SELECT * FROM scenery_index WHERE upload_status = 'uploaded' ORDER BY year, entry_number"
    if limit:
        query += f" LIMIT {limit}"

    rows = uploader_conn.execute(query).fetchall()

    if not rows:
        print("No uploaded photos found in scenery_index.")
        uploader_conn.close()
        main_conn.close()
        return

    # Statistics
    stats = {
        "total": len(rows),
        "imported": 0,
        "skipped_existing": 0,
        "errors": 0,
    }
    errors_list: list[str] = []
    inserts: list[dict] = []

    main_cursor = main_conn.cursor()

    for row in rows:
        oss_key = row["oss_key"]
        photo_id = generate_deterministic_uuid(oss_key)

        # Check if already exists (idempotency)
        existing = main_cursor.execute(
            "SELECT id FROM photos WHERE id = ?", (photo_id,)
        ).fetchone()
        if existing:
            stats["skipped_existing"] += 1
            continue

        try:
            # Build field values
            filename = row["original_filename"]
            if not filename:
                filename = Path(oss_key).name

            file_ext = (row["file_ext"] or "").lower()
            mime_type = get_mime_type(file_ext)
            category = category_to_english(row["category"] or "纪实类")
            description = build_description(row)
            created_at = parse_iso_timestamp(row["upload_timestamp"])
            if not created_at:
                created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            record = {
                "id": photo_id,
                "uploader_id": uploader_id,
                "filename": filename,
                "original_path": oss_key,
                "thumb_path": None,
                "processed_path": None,
                "width": None,
                "height": None,
                "file_size": row["file_size_bytes"],
                "mime_type": mime_type,
                "season": None,
                "category": category,
                "campus": "昌平",
                "description": description,
                "exif_data": "{}",
                "status": "pending",
                "processing_status": "pending",
                "created_at": created_at,
                "updated_at": created_at,
                "captured_at": None,
                "published_at": None,
                "views": 0,
            }

            if apply:
                main_cursor.execute(
                    """INSERT INTO photos (
                        id, uploader_id, filename, original_path, thumb_path, processed_path,
                        width, height, file_size, mime_type, season, category, campus,
                        description, exif_data, status, processing_status,
                        created_at, updated_at, captured_at, published_at, views
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record["id"], record["uploader_id"], record["filename"],
                        record["original_path"], record["thumb_path"], record["processed_path"],
                        record["width"], record["height"], record["file_size"],
                        record["mime_type"], record["season"], record["category"],
                        record["campus"], record["description"], record["exif_data"],
                        record["status"], record["processing_status"],
                        record["created_at"], record["updated_at"],
                        record["captured_at"], record["published_at"], record["views"],
                    ),
                )
                stats["imported"] += 1
            else:
                inserts.append(record)
                stats["imported"] += 1

        except Exception as exc:
            stats["errors"] += 1
            errors_list.append(f"[{oss_key}] {exc}")

    if apply:
        main_conn.commit()

    # Print summary
    mode_label = "(PREVIEW - no changes written)" if not apply else "(APPLY MODE)"
    print(f"\n{'=' * 60}")
    print(f"OSS Photo Import {mode_label}")
    print(f"{'=' * 60}")
    print(f"Uploader DB: {UPLOADER_DB_PATH}")
    print(f"Main DB:     {DB_PATH}")
    print(f"")
    print(f"Total photos in uploader:      {stats['total']}")
    print(f"Newly imported:                {stats['imported']}")
    print(f"Skipped (already exists):      {stats['skipped_existing']}")
    print(f"Errors:                        {stats['errors']}")
    print(f"{'=' * 60}")

    if errors_list:
        print(f"\n[ERRORS] ({len(errors_list)} errors):")
        for e in errors_list[:20]:
            print(f"  - {e}")
        if len(errors_list) > 20:
            print(f"  ... and {len(errors_list) - 20} more")

    if not apply and inserts:
        print(f"\nSample records (first 5):")
        for rec in inserts[:5]:
            print(f"  [{rec['id']}]")
            print(f"    filename:       {rec['filename']}")
            print(f"    original_path:  {rec['original_path']}")
            print(f"    category:       {rec['category']}")
            print(f"    campus:         {rec['campus']}")
            print(f"    description:    {rec['description']}")
            print(f"    file_size:      {rec['file_size']}")
            print(f"    status:         {rec['status']}")
            print(f"    processing:     {rec['processing_status']}")

        print(f"\nThis is PREVIEW mode. To apply changes, run:")
        print(f"  python migrations/import_oss_photos.py --apply")

    elif apply:
        print(f"\n[OK] Import complete! {stats['imported']} records inserted.")

    uploader_conn.close()
    main_conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import OSS photos from BUCTuploader into main database")
    parser.add_argument("--apply", action="store_true", help="Actually apply changes (default: preview)")
    parser.add_argument("--dry-run", action="store_true", help="Synonym for preview mode (default behavior)")
    parser.add_argument("--uploader-id", type=str, default=None, help="UUID of the user to set as uploader")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of photos to process")
    args = parser.parse_args()

    should_apply = args.apply and not args.dry_run
    import_photos(apply=should_apply, uploader_id=args.uploader_id, limit=args.limit)
