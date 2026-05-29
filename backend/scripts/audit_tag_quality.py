#!/usr/bin/env python3
"""
Tag quality audit script.

Analyzes existing tags for quality issues: noise, duplicates, missing coverage,
category balance, and overlap with structured classifications.

Usage:
    python scripts/audit_tag_quality.py
"""
import asyncio
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import engine
from app.services.tag_validation import (
    classify_tag, validate_single_tag, _NOISE_TAGS, _TAG_SYNONYMS, TAG_CATEGORIES
)
from sqlalchemy import text


async def main():
    async with engine.begin() as conn:
        # Get all tags with usage
        tags_result = await conn.execute(
            text("SELECT id, name, category, usage_count FROM tags ORDER BY usage_count DESC")
        )
        all_tags = tags_result.fetchall()

        # Get photo-tag relations
        pt_result = await conn.execute(
            text("SELECT photo_id, tag_id FROM photo_tags")
        )
        photo_tags = pt_result.fetchall()

        # Get photos
        photos_result = await conn.execute(
            text("SELECT id, season, campus, category FROM photos")
        )
        all_photos = photos_result.fetchall()

        # Get photo classifications
        pc_result = await conn.execute(
            text("""
                SELECT photo_id, node_id 
                FROM photo_classifications
            """)
        )
        photo_classifications = pc_result.fetchall()

    # Build reverse map: photo_id -> set of tag names
    tag_id_to_name = {t[0]: t[1] for t in all_tags}
    photo_to_tags = defaultdict(set)
    for photo_id, tag_id in photo_tags:
        photo_to_tags[photo_id].add(tag_id_to_name.get(tag_id, "?"))

    photo_ids_with_tags = set(photo_to_tags.keys())
    all_photo_ids = {p[0] for p in all_photos}

    print("=" * 60)
    print("视觉北化 标签质量审计报告")
    print("=" * 60)

    # 1. Basic stats
    print(f"\n## 基础统计")
    print(f"- 总标签数: {len(all_tags)}")
    print(f"- 总照片数: {len(all_photos)}")
    print(f"- 标签-照片关联: {len(photo_tags)}")
    print(f"- 有标签的照片: {len(photo_ids_with_tags)} ({len(photo_ids_with_tags)/max(len(all_photos),1)*100:.1f}%)")
    print(f"- 无标签的照片: {len(all_photo_ids - photo_ids_with_tags)} ({len(all_photo_ids - photo_ids_with_tags)/max(len(all_photos),1)*100:.1f}%)")

    # Average tags per photo
    tag_counts = [len(tags) for tags in photo_to_tags.values()]
    if tag_counts:
        print(f"- 平均每张照片标签数: {sum(tag_counts)/len(tag_counts):.1f}")
        print(f"- 最少标签数: {min(tag_counts)}")
        print(f"- 最多标签数: {max(tag_counts)}")

    # 2. Category distribution
    print(f"\n## 标签分类分布")
    cat_counter = Counter(t[2] for t in all_tags if t[2])
    for cat, count in cat_counter.most_common():
        cat_name = TAG_CATEGORIES.get(cat, {}).get("name", cat)
        pct = count / len(all_tags) * 100
        bar = "█" * int(pct / 2)
        print(f"  {cat_name:6s} ({cat:8s}): {count:4d} ({pct:5.1f}%) {bar}")

    # 3. Noise detection — run existing tags through validation
    print(f"\n## 噪声标签检测")
    noise_tags = []
    normalized_candidates = []
    for tag_id, name, cat, usage in all_tags:
        result = validate_single_tag(name)
        if not result.is_valid:
            noise_tags.append((name, usage, result.issues))
        elif result.cleaned != name:
            normalized_candidates.append((name, result.cleaned, usage))

    if noise_tags:
        print(f"发现 {len(noise_tags)} 个噪声标签:")
        for name, usage, issues in noise_tags[:20]:
            print(f"  - '{name}' (使用{usage}次): {', '.join(issues)}")
    else:
        print("  ✅ 未发现噪声标签")

    if normalized_candidates:
        print(f"\n可规范化的标签 ({len(normalized_candidates)} 个):")
        for old, new, usage in normalized_candidates[:20]:
            print(f"  - '{old}' → '{new}' (使用{usage}次)")

    # 4. Redundant tags — tags that duplicate structured classifications
    print(f"\n## 冗余标签检测（与结构化分类重叠）")
    season_words = {"春季", "夏季", "秋季", "冬季", "春天", "夏天", "秋天", "冬天"}
    campus_words = {"朝阳校区", "昌平校区", "海淀校区", "校园"}
    redundant = []
    for tag_id, name, cat, usage in all_tags:
        if name in season_words or name in campus_words:
            redundant.append((name, usage, "与 season/campus 分类重叠"))
        elif name in {"风光类", "纪实类", "风光", "纪实"}:
            redundant.append((name, usage, "与 photo_type 分类重叠"))

    if redundant:
        print(f"发现 {len(redundant)} 个冗余标签:")
        for name, usage, reason in redundant:
            print(f"  - '{name}' (使用{usage}次): {reason}")
    else:
        print("  ✅ 未发现冗余标签")

    # 5. Very generic tags (low information value)
    print(f"\n## 低信息量标签（过于笼统）")
    generic_threshold = 10  # tags used on >10% of photos
    generic_tags = [(name, usage) for _, name, _, usage in all_tags 
                    if usage > len(all_photos) * 0.1]
    if generic_tags:
        print(f"以下标签出现在 >10% 的照片中，信息量较低:")
        for name, usage in sorted(generic_tags, key=lambda x: -x[1]):
            pct = usage / len(all_photos) * 100
            print(f"  - '{name}': {usage}张照片 ({pct:.1f}%)")
    else:
        print("  ✅ 无过于笼统的标签")

    # 6. Orphan tags (used only once)
    print(f"\n## 孤立标签（仅使用1次）")
    orphan_tags = [(name, cat) for _, name, cat, usage in all_tags if usage <= 1]
    print(f"孤立标签数: {len(orphan_tags)} ({len(orphan_tags)/max(len(all_photos),1)*100:.1f}%)")
    if orphan_tags:
        print("示例:")
        for name, cat in orphan_tags[:15]:
            print(f"  - '{name}' (分类: {cat or '无'})")

    # 7. Tag length distribution
    print(f"\n## 标签长度分布")
    len_counter = Counter(len(name) for _, name, _, _ in all_tags)
    for length in sorted(len_counter.keys()):
        count = len_counter[length]
        bar = "█" * min(count, 50)
        print(f"  {length}字: {count:4d} {bar}")

    # 8. Photos with too few tags
    print(f"\n## 标签覆盖度不足的照片")
    sparse_photos = [(pid, len(tags)) for pid, tags in photo_to_tags.items() if len(tags) < 3]
    print(f"标签数 <3 的照片: {len(sparse_photos)} ({len(sparse_photos)/max(len(photo_ids_with_tags),1)*100:.1f}%)")

    # 9. Summary
    print(f"\n## 总结")
    total_issues = len(noise_tags) + len(redundant) + len(generic_tags)
    print(f"- 噪声标签: {len(noise_tags)}")
    print(f"- 可规范化: {len(normalized_candidates)}")
    print(f"- 冗余标签: {len(redundant)}")
    print(f"- 笼统标签: {len(generic_tags)}")
    print(f"- 孤立标签: {len(orphan_tags)}")
    print(f"- 覆盖不足照片: {len(sparse_photos)}")
    print(f"- 无标签照片: {len(all_photo_ids - photo_ids_with_tags)}")
    print(f"\n总体质量评分: ", end="")
    issue_rate = total_issues / max(len(all_tags), 1)
    if issue_rate < 0.05:
        print("优秀 ✅")
    elif issue_rate < 0.15:
        print("良好 👍")
    elif issue_rate < 0.30:
        print("一般 ⚠️")
    else:
        print("需要改进 ❌")


if __name__ == "__main__":
    asyncio.run(main())
