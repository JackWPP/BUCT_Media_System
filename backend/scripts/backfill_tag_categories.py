#!/usr/bin/env python3
"""
Backfill tag categories for existing tags.

Uses the classify_tag() function from tag_validation.py to assign categories
to all tags that currently have NULL category.

Usage:
    python scripts/backfill_tag_categories.py --dry-run    # Preview changes
    python scripts/backfill_tag_categories.py              # Apply changes
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import engine
from app.services.tag_validation import classify_tag, TAG_CATEGORIES
from sqlalchemy import text


async def main(dry_run: bool = False):
    async with engine.begin() as conn:
        # Get all tags with NULL or empty category
        result = await conn.execute(
            text("SELECT id, name, category FROM tags WHERE category IS NULL OR category = ''")
        )
        tags = result.fetchall()

    print(f"Found {len(tags)} tags without category\n")

    # Classify each tag
    updates = []
    category_stats = {}
    unclassified = []

    for tag_id, name, current_cat in tags:
        new_cat = classify_tag(name)
        if new_cat:
            updates.append((tag_id, name, new_cat))
            category_stats[new_cat] = category_stats.get(new_cat, 0) + 1
        else:
            unclassified.append(name)

    # Print category distribution
    print("Category distribution:")
    print("-" * 40)
    for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
        cat_name = TAG_CATEGORIES.get(cat, {}).get("name", cat)
        print(f"  {cat_name:8s} ({cat:10s}): {count:4d}")
    print(f"  {'未分类':8s}              : {len(unclassified):4d}")
    print(f"  {'总计':8s}              : {len(tags):4d}")
    print()

    if unclassified:
        print(f"Unclassified tags ({len(unclassified)}):")
        for name in unclassified[:30]:
            print(f"  - {name}")
        if len(unclassified) > 30:
            print(f"  ... and {len(unclassified) - 30} more")
        print()

    if dry_run:
        print("[DRY RUN] No changes made. Run without --dry-run to apply.")
        return

    # Apply updates
    async with engine.begin() as conn:
        for tag_id, name, new_cat in updates:
            await conn.execute(
                text("UPDATE tags SET category = :cat WHERE id = :id"),
                {"cat": new_cat, "id": tag_id},
            )

    print(f"Updated {len(updates)} tags with categories.")

    # Show final distribution
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT category, count(*) FROM tags GROUP BY category ORDER BY count DESC")
        )
        rows = result.fetchall()

    print("\nFinal tag category distribution:")
    print("-" * 40)
    for cat, count in rows:
        cat_display = cat or "(NULL)"
        cat_name = TAG_CATEGORIES.get(cat, {}).get("name", cat_display) if cat else cat_display
        print(f"  {cat_name:12s}: {count:4d}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill tag categories")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
