#!/usr/bin/env python3
"""
Tag data cleanup script.

Normalizes synonyms, removes noise tags, and removes redundant tags
that duplicate structured classifications (season, campus, photo_type).

Usage:
    python scripts/cleanup_tags.py --dry-run    # Preview
    python scripts/cleanup_tags.py              # Apply
"""
import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import engine
from app.services.tag_validation import _TAG_SYNONYMS, _NOISE_TAGS
from sqlalchemy import text


# Tags that duplicate structured classifications (season/campus/photo_type)
_REDUNDANT_TAGS = frozenset({
    "春季", "夏季", "秋季", "冬季", "春天", "夏天", "秋天", "冬天",
    "朝阳校区", "昌平校区", "海淀校区",
    "风光类", "纪实类", "风光", "纪实",
})


async def main(dry_run: bool = False):
    print("=" * 60)
    print("视觉北化 标签数据清洗")
    print("=" * 60)

    async with engine.begin() as conn:
        # 1. Synonym normalization
        print("\n## 1. 同义词规范化")
        for old_name, new_name in _TAG_SYNONYMS.items():
            result = await conn.execute(
                text("SELECT id, usage_count FROM tags WHERE name = :name"),
                {"name": old_name}
            )
            row = result.fetchone()
            if not row:
                continue

            old_id, usage = row
            print(f"  '{old_name}' → '{new_name}' ({usage} 次关联)")

            if dry_run:
                continue

            # Check if target tag exists
            target = await conn.execute(
                text("SELECT id FROM tags WHERE name = :name"),
                {"name": new_name}
            )
            target_row = target.fetchone()

            if target_row:
                target_id = target_row[0]
                # Migrate photo_tags from old to new (skip duplicates)
                await conn.execute(text("""
                    INSERT INTO photo_tags (photo_id, tag_id, created_at)
                    SELECT pt.photo_id, :target_id, pt.created_at FROM photo_tags pt
                    WHERE pt.tag_id = :old_id
                    ON CONFLICT DO NOTHING
                """), {"old_id": old_id, "target_id": target_id})
                # Update usage_count on target
                await conn.execute(text("""
                    UPDATE tags SET usage_count = (
                        SELECT count(*) FROM photo_tags WHERE tag_id = :target_id
                    ) WHERE id = :target_id
                """), {"target_id": target_id})
                # Delete old tag relations and tag
                await conn.execute(text("DELETE FROM photo_tags WHERE tag_id = :id"), {"id": old_id})
                await conn.execute(text("DELETE FROM tags WHERE id = :id"), {"id": old_id})
            else:
                # Just rename
                await conn.execute(
                    text("UPDATE tags SET name = :new_name WHERE id = :id"),
                    {"new_name": new_name, "id": old_id}
                )

        # 2. Remove noise tags
        print("\n## 2. 删除噪声标签")
        for noise_tag in _NOISE_TAGS:
            result = await conn.execute(
                text("SELECT id, usage_count FROM tags WHERE name = :name"),
                {"name": noise_tag}
            )
            row = result.fetchone()
            if not row:
                continue

            tag_id, usage = row
            print(f"  删除: '{noise_tag}' ({usage} 次关联)")

            if dry_run:
                continue

            await conn.execute(text("DELETE FROM photo_tags WHERE tag_id = :id"), {"id": tag_id})
            await conn.execute(text("DELETE FROM tags WHERE id = :id"), {"id": tag_id})

        # 3. Remove redundant tags (duplicating classifications)
        print("\n## 3. 删除冗余标签（与分类重复）")
        for redundant in _REDUNDANT_TAGS:
            result = await conn.execute(
                text("SELECT id, usage_count FROM tags WHERE name = :name"),
                {"name": redundant}
            )
            row = result.fetchone()
            if not row:
                continue

            tag_id, usage = row
            print(f"  删除: '{redundant}' ({usage} 次关联)")

            if dry_run:
                continue

            await conn.execute(text("DELETE FROM photo_tags WHERE tag_id = :id"), {"id": tag_id})
            await conn.execute(text("DELETE FROM tags WHERE id = :id"), {"id": tag_id})

        # 4. Update usage_count for all tags
        if not dry_run:
            print("\n## 4. 更新 usage_count")
            await conn.execute(text("""
                UPDATE tags SET usage_count = (
                    SELECT count(*) FROM photo_tags WHERE tag_id = tags.id
                )
            """))
            print("  ✅ usage_count 已更新")

        # Final stats
        result = await conn.execute(text("SELECT count(*) FROM tags"))
        total_tags = result.scalar()
        result = await conn.execute(text("SELECT count(*) FROM photo_tags"))
        total_relations = result.scalar()
        result = await conn.execute(text("""
            SELECT count(*) FROM photos p
            WHERE NOT EXISTS (SELECT 1 FROM photo_tags pt WHERE pt.photo_id = p.id)
        """))
        no_tag_photos = result.scalar()

    print(f"\n## 最终统计")
    print(f"  总标签数: {total_tags}")
    print(f"  总关联数: {total_relations}")
    print(f"  无标签照片: {no_tag_photos}")

    if dry_run:
        print("\n[DRY RUN] 未做任何修改。去掉 --dry-run 执行。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
