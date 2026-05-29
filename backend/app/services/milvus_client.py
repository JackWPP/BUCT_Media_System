"""
Milvus vector database client for photo vector storage and retrieval.

Provides async-friendly wrappers around ``pymilvus`` for:
- Inserting photo tag/attribute embeddings
- Vector similarity search with optional structured filters
- Deleting vectors by photo ID

Connection is established lazily on first use.  If Milvus is
unavailable, operations return safe defaults and log warnings.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Milvus connection settings
_MILVUS_HOST = "localhost"
_MILVUS_PORT = 19530

# Collection settings
_COLLECTION_NAME = "photo_vectors"
_EMBEDDING_DIM = 512  # bge-small-zh-v1.5 dimensionality
_INDEX_TYPE = "HNSW"
_METRIC_TYPE = "COSINE"
_INDEX_PARAMS = {"M": 16, "efConstruction": 200}
_SEARCH_PARAMS = {"ef": 256}


class MilvusSearchClient:
    """Async-friendly Milvus client for photo vector operations.

    Connections are established lazily — the first operation will
    attempt to connect, and failures are logged (never raised).
    """

    def __init__(self) -> None:
        self._connected = False
        self._collection: Optional[Any] = None  # pymilvus.Collection

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _ensure_connection(self) -> bool:
        """Connect to Milvus and load the collection.

        Returns ``True`` if the collection is ready for use.
        """
        if self._connected and self._collection is not None:
            return True
        try:
            from pymilvus import connections, Collection, utility  # noqa: F811

            # Connect (idempotent — pymilvus deduplicates by alias)
            alias = "visual_buct_default"
            try:
                connections.connect(
                    alias=alias,
                    host=_MILVUS_HOST,
                    port=_MILVUS_PORT,
                )
            except Exception:
                # May already be connected — try to proceed
                pass

            # Check if collection exists
            if not utility.has_collection(_COLLECTION_NAME, using=alias):
                logger.warning(
                    "MilvusSearchClient: collection '%s' does not exist yet. "
                    "Run setup_photo_vectors() to create it.",
                    _COLLECTION_NAME,
                )
                self._connected = False
                return False

            self._collection = Collection(_COLLECTION_NAME, using=alias)
            self._collection.load()
            self._connected = True
            logger.info(
                "MilvusSearchClient: connected, collection '%s' loaded (%d entities)",
                _COLLECTION_NAME,
                self._collection.num_entities,
            )
            return True
        except ImportError:
            logger.error(
                "MilvusSearchClient: 'pymilvus' not installed. "
                "Vector search features will be unavailable."
            )
            return False
        except Exception as exc:
            logger.warning("MilvusSearchClient: connection failed — %s", exc)
            self._connected = False
            return False

    # ------------------------------------------------------------------
    # Collection setup
    # ------------------------------------------------------------------

    def setup_collection(self) -> bool:
        """Create the ``photo_vectors`` collection if it doesn't exist.

        Schema:
        - photo_id:  VARCHAR (primary key, max 64)
        - vector:    FLOAT_VECTOR[1024]
        - tag_text:  VARCHAR (max 500)
        - category:  VARCHAR (max 100)
        - created_at: INT64 (unix timestamp)

        Returns ``True`` on success.
        """
        try:
            from pymilvus import (  # noqa: F811
                connections,
                Collection,
                CollectionSchema,
                FieldSchema,
                DataType,
                utility,
            )

            alias = "visual_buct_default"
            try:
                connections.connect(alias=alias, host=_MILVUS_HOST, port=_MILVUS_PORT)
            except Exception:
                pass

            if utility.has_collection(_COLLECTION_NAME, using=alias):
                logger.info("MilvusSearchClient: collection '%s' already exists", _COLLECTION_NAME)
                return True

            fields = [
                FieldSchema(name="photo_id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=_EMBEDDING_DIM),
                FieldSchema(name="tag_text", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="created_at", dtype=DataType.INT64),
            ]
            schema = CollectionSchema(fields=fields, description="Photo vector embeddings for visual-buct")
            collection = Collection(name=_COLLECTION_NAME, schema=schema, using=alias)

            # Create HNSW index on vector field
            collection.create_index(
                field_name="vector",
                index_params={
                    "index_type": _INDEX_TYPE,
                    "metric_type": _METRIC_TYPE,
                    "params": _INDEX_PARAMS,
                },
            )
            logger.info("MilvusSearchClient: collection '%s' created with HNSW index", _COLLECTION_NAME)
            return True
        except Exception as exc:
            logger.error("MilvusSearchClient: setup_collection failed — %s", exc)
            return False

    # ------------------------------------------------------------------
    # Sync core operations (called via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _insert_sync(
        self,
        photo_id: str,
        vectors: list[dict[str, Any]],
    ) -> bool:
        """Insert one or more vector records for a photo.

        Each item in *vectors* should be a dict with keys:
        ``vector`` (list[float]), ``tag_text`` (str), ``category`` (str).

        The ``created_at`` field is set to the current unix timestamp.
        """
        if not self._ensure_connection():
            return False
        try:
            now_ts = int(time.time())
            rows = []
            for item in vectors:
                rows.append({
                    "photo_id": photo_id,
                    "vector": item["vector"],
                    "tag_text": item.get("tag_text", ""),
                    "category": item.get("category", ""),
                    "created_at": now_ts,
                })

            self._collection.insert(rows)
            self._collection.flush()
            logger.debug("MilvusSearchClient: inserted %d vectors for photo %s", len(vectors), photo_id)
            return True
        except Exception as exc:
            logger.error("MilvusSearchClient: insert failed — %s", exc)
            return False

    def _search_sync(
        self,
        query_vector: list[float],
        limit: int = 20,
        filters: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Perform a vector similarity search.

        Args:
            query_vector: The 1024-dim query embedding.
            limit:        Max results to return.
            filters:      Optional Milvus boolean expression
                          (e.g. ``'category == "landscape"'``).

        Returns a list of dicts: ``{photo_id, score, tag_text, category, created_at}``.
        """
        if not self._ensure_connection():
            return []
        try:
            search_params = {
                "metric_type": _METRIC_TYPE,
                "params": _SEARCH_PARAMS,
            }
            output_fields = ["photo_id", "tag_text", "category", "created_at"]

            results = self._collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=limit,
                expr=filters,
                output_fields=output_fields,
            )

            hits: list[dict[str, Any]] = []
            for hit in results[0]:
                entity = hit.entity
                hits.append({
                    "photo_id": entity.get("photo_id"),
                    "score": float(hit.distance),
                    "tag_text": entity.get("tag_text", ""),
                    "category": entity.get("category", ""),
                    "created_at": entity.get("created_at", 0),
                })
            return hits
        except Exception as exc:
            logger.error("MilvusSearchClient: search failed — %s", exc)
            return []

    def _delete_sync(self, photo_id: str) -> bool:
        """Delete all vectors associated with a photo."""
        if not self._ensure_connection():
            return False
        try:
            self._collection.delete(f'photo_id == "{photo_id}"')
            self._collection.flush()
            logger.debug("MilvusSearchClient: deleted vectors for photo %s", photo_id)
            return True
        except Exception as exc:
            logger.error("MilvusSearchClient: delete failed — %s", exc)
            return False

    # ------------------------------------------------------------------
    # Async public API
    # ------------------------------------------------------------------

    async def insert_vectors(self, photo_id: str, vectors: list[dict[str, Any]]) -> bool:
        """Insert vector records for a photo (async)."""
        return await asyncio.to_thread(self._insert_sync, photo_id, vectors)

    async def search_vectors(
        self,
        query_vector: list[float],
        limit: int = 20,
        filters: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Vector similarity search (async)."""
        return await asyncio.to_thread(self._search_sync, query_vector, limit, filters)

    async def delete_by_photo(self, photo_id: str) -> bool:
        """Delete all vectors for a photo (async)."""
        return await asyncio.to_thread(self._delete_sync, photo_id)


# ---- Module-level singleton ----
_client: Optional[MilvusSearchClient] = None


def get_milvus_client() -> MilvusSearchClient:
    """Return (and lazily create) the global MilvusSearchClient instance."""
    global _client
    if _client is None:
        _client = MilvusSearchClient()
    return _client
