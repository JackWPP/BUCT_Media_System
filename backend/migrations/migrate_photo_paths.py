r"""
Database migration: convert absolute paths in photos table to relative paths.

Problem:
- Photos imported via the bulk import endpoint stored the external absolute path
  in original_path (e.g. F:\Origin\campus_summer.jpg)
- But the files were already copied to uploads/originals/{uuid}.jpg
- The database still held the external path, causing FileResponse 500 errors

Migration strategy:
1. original_path: find the file in uploads/originals/ by UUID + extension,
   update to originals/{uuid}{ext}
2. thumb_path: convert uploads/thumbnails/xxx to thumbnails/xxx
3. Warn if the expected file does not exist in uploads/

Usage:
    cd backend
    python migrations/migrate_photo_paths.py          # preview mode
    python migrations/migrate_photo_paths.py --apply   # apply changes
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

DB_PATH = "buct_media.db"
UPLOAD_DIR = "./uploads"

ORIG_DIR_NAME = "originals"
THUMB_DIR_NAME = "thumbnails"


def _is_already_correct_relative(path: str, prefix: str) -> bool:
    if not path:
        return True
    cleaned = path.replace("\\", "/")
    return cleaned.startswith(prefix + "/")


def migrate(apply: bool = False):
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, filename, original_path, thumb_path, processed_path FROM photos")
    rows = cursor.fetchall()

    if not rows:
        print("No photo records found. Nothing to migrate.")
        conn.close()
        return

    orig_dir = os.path.join(UPLOAD_DIR, ORIG_DIR_NAME)

    stats = {
        "total": len(rows),
        "orig_already_correct": 0,
        "orig_fixed_from_external": 0,
        "orig_fixed_from_abs_uploads": 0,
        "orig_fixed_from_uploads_prefix": 0,
        "orig_missing_file": 0,
        "thumb_already_correct": 0,
        "thumb_fixed_from_uploads_prefix": 0,
        "thumb_fixed_from_abs_uploads": 0,
        "updated_count": 0,
    }
    warnings = []
    updates = []

    for row in rows:
        photo_id = row["id"]
        filename = row["filename"]
        orig_path = row["original_path"] or ""
        thumb_path = row["thumb_path"] or ""
        processed_path = row["processed_path"] or ""

        new_orig = orig_path
        new_thumb = thumb_path
        new_processed = processed_path
        changed = False

        # --- Handle original_path ---
        if orig_path:
            cleaned_orig = orig_path.replace("\\", "/")

            if _is_already_correct_relative(cleaned_orig, ORIG_DIR_NAME):
                stats["orig_already_correct"] += 1
            elif cleaned_orig.startswith("uploads/"):
                new_orig = cleaned_orig[len("uploads/"):]
                stats["orig_fixed_from_uploads_prefix"] += 1
                changed = True
            elif os.path.isabs(cleaned_orig):
                upload_abs = os.path.abspath(UPLOAD_DIR).replace("\\", "/")
                if cleaned_orig.startswith(upload_abs + "/"):
                    new_orig = cleaned_orig[len(upload_abs) + 1:]
                    stats["orig_fixed_from_abs_uploads"] += 1
                    changed = True
                else:
                    ext = Path(filename).suffix.lower()
                    if not ext:
                        for e in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
                            candidate = os.path.join(orig_dir, f"{photo_id}{e}")
                            if os.path.exists(candidate):
                                ext = e
                                break
                    expected_file = os.path.join(orig_dir, f"{photo_id}{ext}")
                    if os.path.exists(expected_file):
                        new_orig = f"originals/{photo_id}{ext}"
                        stats["orig_fixed_from_external"] += 1
                        changed = True
                    else:
                        stats["orig_missing_file"] += 1
                        warnings.append(
                            f"[{photo_id}] original_path: external path '{orig_path}' "
                            f"and no file found at '{expected_file}'"
                        )

        # --- Handle thumb_path ---
        if thumb_path:
            cleaned_thumb = thumb_path.replace("\\", "/")

            if _is_already_correct_relative(cleaned_thumb, THUMB_DIR_NAME):
                stats["thumb_already_correct"] += 1
            elif cleaned_thumb.startswith("uploads/"):
                new_thumb = cleaned_thumb[len("uploads/"):]
                stats["thumb_fixed_from_uploads_prefix"] += 1
                changed = True
            elif os.path.isabs(cleaned_thumb):
                upload_abs = os.path.abspath(UPLOAD_DIR).replace("\\", "/")
                if cleaned_thumb.startswith(upload_abs + "/"):
                    new_thumb = cleaned_thumb[len(upload_abs) + 1:]
                    stats["thumb_fixed_from_abs_uploads"] += 1
                    changed = True

        # --- Handle processed_path ---
        if processed_path:
            cleaned_proc = processed_path.replace("\\", "/")
            if cleaned_proc.startswith("uploads/"):
                new_processed = cleaned_proc[len("uploads/"):]
                changed = True
            elif os.path.isabs(cleaned_proc):
                upload_abs = os.path.abspath(UPLOAD_DIR).replace("\\", "/")
                if cleaned_proc.startswith(upload_abs + "/"):
                    new_processed = cleaned_proc[len(upload_abs) + 1:]
                    changed = True

        if changed:
            updates.append((new_orig, new_thumb, new_processed, photo_id))

    mode_label = "(PREVIEW - no changes written)" if not apply else "(APPLY MODE)"
    print(f"\n{'=' * 60}")
    print(f"Photo Path Migration {mode_label}")
    print(f"{'=' * 60}")
    print(f"Total records:                {stats['total']}")
    print(f"")
    print(f"original_path:")
    print(f"  Already correct (originals/...):   {stats['orig_already_correct']}")
    print(f"  Fixed from uploads/... prefix:     {stats['orig_fixed_from_uploads_prefix']}")
    print(f"  Fixed from abs path in uploads/:   {stats['orig_fixed_from_abs_uploads']}")
    print(f"  Fixed from external path:          {stats['orig_fixed_from_external']}")
    print(f"  Missing file (cannot fix):         {stats['orig_missing_file']}")
    print(f"")
    print(f"thumb_path:")
    print(f"  Already correct (thumbnails/...):  {stats['thumb_already_correct']}")
    print(f"  Fixed from uploads/... prefix:     {stats['thumb_fixed_from_uploads_prefix']}")
    print(f"  Fixed from abs path in uploads/:   {stats['thumb_fixed_from_abs_uploads']}")
    print(f"")
    print(f"Records to update:           {len(updates)}")
    print(f"{'=' * 60}")

    if warnings:
        print(f"\n[WARNINGS] ({len(warnings)} records with missing files):")
        for w in warnings[:30]:
            print(f"  - {w}")
        if len(warnings) > 30:
            print(f"  ... and {len(warnings) - 30} more")

    if updates:
        print(f"\nSample updates (first 10):")
        for orig, thumb, processed, pid in updates[:10]:
            print(f"  [{pid}]")
            print(f"    original_path  -> {orig}")
            if thumb:
                print(f"    thumb_path     -> {thumb}")
            if processed:
                print(f"    processed_path -> {processed}")

    if not apply:
        print(f"\nThis is PREVIEW mode. To apply changes, run:")
        print(f"  python migrations/migrate_photo_paths.py --apply")
    else:
        for orig, thumb, processed, pid in updates:
            cursor.execute(
                "UPDATE photos SET original_path = ?, thumb_path = ?, processed_path = ? WHERE id = ?",
                (orig, thumb, processed, pid),
            )
            stats["updated_count"] += 1
        conn.commit()
        print(f"\n[OK] Migration complete! Updated {stats['updated_count']} records.")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate photo paths to relative format")
    parser.add_argument("--apply", action="store_true", help="Actually apply changes (default: preview)")
    args = parser.parse_args()
    migrate(apply=args.apply)
