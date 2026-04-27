"""
Database migration: rename 'building' taxonomy facet to 'landmark'.

This migrates the existing taxonomy from the narrow "building" (楼宇) concept
to the broader "landmark" (地标) concept that includes both buildings and
natural/scenic landmarks like 柳湖, 樱花大道, 操场, etc.

Also creates new landmark nodes and aliases that were added in the updated
DEFAULT_TAXONOMY.

Usage:
    cd backend
    python migrations/migrate_building_to_landmark.py          # preview mode
    python migrations/migrate_building_to_landmark.py --apply   # apply changes
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime

DB_PATH = "visual_buct.db"

# New landmark nodes to add (beyond existing building nodes)
NEW_LANDMARK_NODES = [
    # 建筑类 (new additions beyond original 4)
    ("三教", "三教", 5),
    ("实验楼", "实验楼", 6),
    ("行政楼", "行政楼", 7),
    ("体育馆", "体育馆", 8),
    ("学生活动中心", "学生活动中心", 9),
    ("主楼", "主楼", 10),
    ("科技大厦", "科技大厦", 11),
    # 自然/区域类
    ("柳湖", "柳湖", 12),
    ("樱花大道", "樱花大道", 13),
    ("操场", "操场", 14),
    ("校门", "校门", 15),
    ("主楼广场", "主楼广场", 16),
]

# Aliases to add: (node_name, alias)
LANDMARK_ALIASES = [
    ("图书馆", "北化图书馆"),
    ("图书馆", "新图书馆"),
    ("樱花苑学生公寓", "樱花苑"),
    ("樱花苑学生公寓", "樱花苑公寓"),
    ("学生活动中心", "活动中心"),
    ("学生活动中心", "学生中心"),
    ("柳湖", "湖"),
    ("柳湖", "校园湖"),
    ("柳湖", "学校湖"),
    ("樱花大道", "樱花路"),
    ("樱花大道", "樱花园"),
    ("校门", "北门"),
    ("校门", "南门"),
    ("校门", "东门"),
    ("校门", "西门"),
    ("校门", "正门"),
    ("一教", "第一教学楼"),
    ("二教", "第二教学楼"),
    ("三教", "第三教学楼"),
    ("实验楼", "实验中心"),
    ("实验楼", "综合实验楼"),
    ("行政楼", "办公楼"),
    ("行政楼", "行政办公楼"),
    ("体育馆", "体育中心"),
    ("体育馆", "室内体育馆"),
    ("主楼", "学校主楼"),
    ("主楼", "中心主楼"),
]

# Aliases for other facets
SEASON_ALIASES = [
    ("春季", "春天"), ("春季", "春日"), ("春季", "春"),
    ("夏季", "夏天"), ("夏季", "夏日"), ("夏季", "夏"),
    ("秋季", "秋天"), ("秋季", "秋日"), ("秋季", "秋"), ("秋季", "金秋"),
    ("冬季", "冬天"), ("冬季", "冬日"), ("冬季", "冬"),
]

CAMPUS_ALIASES = [
    ("昌平校区", "昌平"), ("昌平校区", "北化昌平"),
    ("朝阳校区", "朝阳"), ("朝阳校区", "北化朝阳"),
]

GALLERY_SERIES_ALIASES = [
    ("摄影大赛", "摄影比赛"), ("摄影大赛", "摄影大赛作品"),
    ("校园风光", "校园景色"), ("校园风光", "校园风景"),
    ("活动纪实", "校园活动纪实"),
]

PHOTO_TYPE_ALIASES = [
    ("风光", "风景"), ("风光", "风景照"), ("风光", "自然风光"), ("风光", "景色"), ("风光", "风光摄影"),
    ("纪实", "记录"), ("纪实", "纪实摄影"), ("纪实", "记录片"),
    ("人像", "人物"), ("人像", "人物照"), ("人像", "肖像"),
    ("活动", "活动照"), ("活动", "集体活动"),
]

ALL_ALIASES = SEASON_ALIASES + CAMPUS_ALIASES + GALLERY_SERIES_ALIASES + PHOTO_TYPE_ALIASES


def migrate(apply: bool = False):
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    mode_label = "(PREVIEW)" if not apply else "(APPLY)"

    # Step 1: Rename building facet to landmark
    print(f"\n{'=' * 60}")
    print(f"Building → Landmark Migration {mode_label}")
    print(f"{'=' * 60}")

    facet_row = cursor.execute(
        "SELECT id, key, name FROM taxonomy_facets WHERE key = 'building'"
    ).fetchone()

    if facet_row is None:
        print("No 'building' facet found. Checking if 'landmark' already exists...")
        landmark = cursor.execute(
            "SELECT id, key, name FROM taxonomy_facets WHERE key = 'landmark'"
        ).fetchone()
        if landmark:
            print(f"  'landmark' facet already exists (id={landmark['id']}). Skipping rename.")
            facet_id = landmark["id"]
        else:
            print("  Neither 'building' nor 'landmark' facet found. Nothing to migrate.")
            conn.close()
            return
    else:
        facet_id = facet_row["id"]
        print(f"Found 'building' facet (id={facet_id}):")
        print(f"  Current: key='building', name='楼宇'")
        print(f"  Target:  key='landmark', name='地标'")
        if apply:
            cursor.execute(
                "UPDATE taxonomy_facets SET key = 'landmark', name = '地标' WHERE id = ?",
                (facet_id,),
            )
            print("  [OK] Updated.")

    # Step 2: Add new landmark nodes
    print(f"\n--- Adding new landmark nodes ---")
    existing_nodes = {
        row["name"]: row["id"]
        for row in cursor.execute(
            "SELECT id, name FROM taxonomy_nodes WHERE facet_id = ?", (facet_id,)
        ).fetchall()
    }
    print(f"Existing nodes: {list(existing_nodes.keys())}")

    nodes_added = 0
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for name, key, sort_order in NEW_LANDMARK_NODES:
        if name in existing_nodes:
            print(f"  Skip (exists): {name}")
            continue
        if apply:
            cursor.execute(
                "INSERT INTO taxonomy_nodes (facet_id, key, name, sort_order, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                (facet_id, key, name, sort_order, now, now),
            )
        nodes_added += 1
        print(f"  Add: {name}")

    if apply and nodes_added:
        conn.commit()
    print(f"New nodes to add: {nodes_added}")

    # Step 3: Add landmark aliases
    print(f"\n--- Adding landmark aliases ---")
    # Re-fetch nodes (includes newly added ones)
    nodes_by_name = {
        row["name"]: row["id"]
        for row in cursor.execute(
            "SELECT id, name FROM taxonomy_nodes WHERE facet_id = ?", (facet_id,)
        ).fetchall()
    }

    # Get existing aliases
    existing_aliases = set()
    for row in cursor.execute(
        "SELECT node_id, alias FROM taxonomy_aliases"
    ).fetchall():
        existing_aliases.add((row["node_id"], row["alias"]))

    landmark_aliases_added = 0
    for node_name, alias in LANDMARK_ALIASES:
        node_id = nodes_by_name.get(node_name)
        if node_id is None:
            continue
        if (node_id, alias) in existing_aliases:
            continue
        if apply:
            cursor.execute(
                "INSERT INTO taxonomy_aliases (node_id, alias, created_at) VALUES (?, ?, ?)",
                (node_id, alias, now),
            )
        landmark_aliases_added += 1
        print(f"  Add alias: {node_name} → {alias}")

    if apply and landmark_aliases_added:
        conn.commit()
    print(f"Landmark aliases to add: {landmark_aliases_added}")

    # Step 4: Add aliases for other facets
    print(f"\n--- Adding aliases for other facets ---")

    # Build a lookup: (facet_key, node_name) → node_id
    facet_key_map = {}
    for frow in cursor.execute("SELECT id, key FROM taxonomy_facets").fetchall():
        facet_key_map[frow["key"]] = frow["id"]

    other_aliases_added = 0
    for node_name, alias in ALL_ALIASES:
        # Find the node across all facets
        node_row = cursor.execute(
            "SELECT n.id, n.facet_id FROM taxonomy_nodes n WHERE n.name = ?",
            (node_name,),
        ).fetchone()
        if node_row is None:
            continue
        node_id = node_row["id"]
        if (node_id, alias) in existing_aliases:
            continue
        if apply:
            cursor.execute(
                "INSERT INTO taxonomy_aliases (node_id, alias, created_at) VALUES (?, ?, ?)",
                (node_id, alias, now),
            )
        other_aliases_added += 1
        print(f"  Add alias: {node_name} → {alias}")

    if apply and other_aliases_added:
        conn.commit()
    print(f"Other aliases to add: {other_aliases_added}")

    # Step 5: Update photo_classifications (facet_id is correct, but check for old data)
    print(f"\n--- Summary ---")
    print(f"Facet renamed:     {'Yes' if facet_row else 'N/A'}")
    print(f"New nodes:         {nodes_added}")
    print(f"Landmark aliases:  {landmark_aliases_added}")
    print(f"Other aliases:     {other_aliases_added}")

    if not apply:
        print(f"\nThis is PREVIEW mode. To apply changes, run:")
        print(f"  python migrations/migrate_building_to_landmark.py --apply")
    else:
        print(f"\n[OK] Migration complete!")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate building taxonomy to landmark")
    parser.add_argument("--apply", action="store_true", help="Actually apply changes (default: preview)")
    args = parser.parse_args()
    migrate(apply=args.apply)
