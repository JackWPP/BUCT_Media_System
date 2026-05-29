#!/usr/bin/env python3
"""
Batch vectorize all existing tags into Milvus (optimized batch insert).
"""
import asyncio
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import engine
from app.services.embedding_service import EmbeddingService
from sqlalchemy import text


async def main(dry_run: bool = False, rebuild: bool = False):
    print("=" * 60)
    print("视觉北化 标签批量向量化 (batch mode)")
    print("=" * 60)

    # 1. Setup Milvus
    from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType
    
    alias = "visual_buct_default"
    connections.connect(alias=alias, host="localhost", port="19530")
    
    if rebuild and utility.has_collection("photo_vectors", using=alias):
        utility.drop_collection("photo_vectors", using=alias)
        print("旧集合已删除")

    if not utility.has_collection("photo_vectors", using=alias):
        fields = [
            FieldSchema(name="photo_id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=512),
            FieldSchema(name="tag_text", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="created_at", dtype=DataType.INT64),
        ]
        schema = CollectionSchema(fields)
        col = Collection("photo_vectors", schema=schema, using=alias)
        col.create_index("vector", {
            "index_type": "HNSW", "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 200}
        })
        print("集合已创建")
    else:
        col = Collection("photo_vectors", using=alias)
    
    col.load()
    print(f"当前向量数: {col.num_entities}")

    # 2. Load model
    emb = EmbeddingService()
    test = emb.encode_text("test")
    if test is None:
        print("❌ 模型加载失败")
        return
    print(f"模型就绪 (dim={len(test)})")

    # 3. Get tags
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT t.id, t.name, t.category, count(pt.photo_id) as usage
            FROM tags t LEFT JOIN photo_tags pt ON pt.tag_id = t.id
            GROUP BY t.id, t.name, t.category ORDER BY usage DESC
        """))
        tags = result.fetchall()

    print(f"标签数: {len(tags)}")

    if dry_run:
        for tid, name, cat, usage in tags[:10]:
            print(f"  [{cat or '?':8s}] {name} ({usage})")
        return

    # 4. Batch encode + insert
    batch_size = 64
    now_ts = int(time.time())
    total = 0
    
    for i in range(0, len(tags), batch_size):
        batch = tags[i:i + batch_size]
        names = [t[1] for t in batch]
        vectors = emb.encode_batch(names)
        if vectors is None:
            continue

        rows = []
        for j, (tag_id, name, category, usage) in enumerate(batch):
            rows.append({
                "photo_id": f"tag_{tag_id}",
                "vector": vectors[j],
                "tag_text": name,
                "category": category or "",
                "created_at": now_ts,
            })

        col.insert(rows)
        total += len(rows)
        print(f"\r  插入: {total}/{len(tags)}", end="", flush=True)

    col.flush()
    print(f"\n\n✅ 完成！共 {total} 个标签向量已入库")
    print(f"  Milvus 实体数: {col.num_entities}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run, rebuild=args.rebuild))
