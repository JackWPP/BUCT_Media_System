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

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Collection settings
_INDEX_TYPE = "HNSW"
_METRIC_TYPE = "COSINE"
_INDEX_PARAMS = {"M": 16, "efConstruction": 200}
_SEARCH_PARAMS = {"ef": 256}
_CONNECTION_ALIAS = "visual_buct_default"


class MilvusSearchClient:
    """Async-friendly Milvus client for photo vector operations.

    Connections are established lazily — the first operation will
    attempt to connect, and failures are logged (never raised).
    """

    def __init__(self, collection_name: Optional[str] = None) -> None:
        settings = get_settings()
        self.collection_name = collection_name or settings.MILVUS_COLLECTION_NAME
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.embedding_dim = settings.MILVUS_EMBEDDING_DIM
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
            try:
                connections.connect(
                    alias=_CONNECTION_ALIAS,
                    host=self.host,
                    port=self.port,
                )
            except Exception:
                # May already be connected — try to proceed
                pass

            # Check if collection exists
            if not utility.has_collection(self.collection_name, using=_CONNECTION_ALIAS):
                logger.warning(
                    "MilvusSearchClient: collection '%s' does not exist yet. "
                    "Run setup_photo_vectors() to create it.",
                    self.collection_name,
                )
                self._connected = False
                return False

            self._collection = Collection(self.collection_name, using=_CONNECTION_ALIAS)
            self._collection.load()
            self._connected = True
            logger.info(
                "MilvusSearchClient: connected, collection '%s' loaded (%d entities)",
                self.collection_name,
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
        """Create the configured photo-level collection if it doesn't exist.

        Schema:
        - photo_id:  VARCHAR (primary key, max 64)
        - vector:    FLOAT_VECTOR[512]
        - embedding_text: VARCHAR (max 4096)
        - source_fields:  VARCHAR (max 500)
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

            try:
                connections.connect(alias=_CONNECTION_ALIAS, host=self.host, port=self.port)
            except Exception:
                pass

            if utility.has_collection(self.collection_name, using=_CONNECTION_ALIAS):
                logger.info("MilvusSearchClient: collection '%s' already exists", self.collection_name)
                return True

            fields = [
                FieldSchema(name="photo_id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
                FieldSchema(name="embedding_text", dtype=DataType.VARCHAR, max_length=4096),
                FieldSchema(name="source_fields", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="created_at", dtype=DataType.INT64),
            ]
            schema = CollectionSchema(fields=fields, description="Photo-level vector embeddings for visual-buct")
            collection = Collection(name=self.collection_name, schema=schema, using=_CONNECTION_ALIAS)

            # Create HNSW index on vector field
            collection.create_index(
                field_name="vector",
                index_params={
                    "index_type": _INDEX_TYPE,
                    "metric_type": _METRIC_TYPE,
                    "params": _INDEX_PARAMS,
                },
            )
            logger.info("MilvusSearchClient: collection '%s' created with HNSW index", self.collection_name)
            return True
        except Exception as exc:
            logger.error("MilvusSearchClient: setup_collection failed — %s", exc)
            return False

    def entity_count(self) -> Optional[int]:
        """Return entity count for the configured collection, or None if unavailable."""
        if not self._ensure_connection():
            return None
        try:
            return int(self._collection.num_entities)
        except Exception as exc:
            logger.warning("MilvusSearchClient: entity_count failed — %s", exc)
            return None

    # ------------------------------------------------------------------
    # Sync core operations (called via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _insert_sync(
        self,
        photo_id: str,
        vectors: list[dict[str, Any]],
    ) -> bool:
        """Insert one or more vector records for a photo.

        Each item in *vectors* should be a dict with ``vector`` plus optional
        ``embedding_text`` and ``source_fields``. Legacy ``tag_text`` and
        ``category`` keys are still accepted for old callers.

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
                    "embedding_text": item.get("embedding_text", item.get("tag_text", "")),
                    "source_fields": item.get("source_fields", item.get("category", "")),
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
            query_vector: The configured-dim query embedding.
            limit:        Max results to return.
            filters:      Optional Milvus boolean expression
                          for fields present in the configured collection.

        Returns a list of dicts: ``{photo_id, score, embedding_text, source_fields, created_at}``.
        """
        if not self._ensure_connection():
            return []
        try:
            search_params = {
                "metric_type": _METRIC_TYPE,
                "params": _SEARCH_PARAMS,
            }
            output_fields = ["photo_id", "embedding_text", "source_fields", "created_at"]

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
                    "embedding_text": entity.get("embedding_text", ""),
                    "source_fields": entity.get("source_fields", ""),
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

    async def get_entity_count(self) -> Optional[int]:
        """Return entity count for the configured collection (async)."""
        return await asyncio.to_thread(self.entity_count)


# ---- Module-level singleton ----
_client: Optional[MilvusSearchClient] = None


def get_milvus_client() -> MilvusSearchClient:
    """Return (and lazily create) the global MilvusSearchClient instance."""
    global _client
    if _client is None:
        _client = MilvusSearchClient()
    return _client
