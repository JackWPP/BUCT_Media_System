"""
Text embedding service using sentence-transformers with BAAI/bge-small-zh-v1.5.

Features:
- Lazy model loading (loaded on first encode call, not at import time)
- CPU-only inference (no CUDA required)
- Local model cache at /data/visual-buct/vector-search/models/bge-small-zh
- Graceful import error handling
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Model configuration — bge-small-zh-v1.5 is fast on CPU (~70 texts/s)
_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
_MODEL_CACHE_DIR = "/data/visual-buct/vector-search/models/bge-small-zh"
_EMBEDDING_DIM = 512


class EmbeddingService:
    """Thin wrapper around ``sentence-transformers`` for bge-m3 embeddings.

    The underlying ``SentenceTransformer`` model is loaded lazily on the
    first call to :meth:`encode_text` or :meth:`encode_batch`.  This
    avoids blocking import time with a multi-hundred-MB model load.
    """

    def __init__(self) -> None:
        self._model: Optional[object] = None  # SentenceTransformer (avoid hard import)
        self._loaded = False

    # ------------------------------------------------------------------
    # Lazy model loader
    # ------------------------------------------------------------------

    def _load_model(self) -> bool:
        """Load the SentenceTransformer model. Returns True on success."""
        if self._loaded and self._model is not None:
            return True

        try:
            from sentence_transformers import SentenceTransformer  # noqa: F811

            cache_dir = Path(_MODEL_CACHE_DIR)
            cache_dir.mkdir(parents=True, exist_ok=True)

            logger.info(
                "EmbeddingService: loading model %s (cache: %s) ...",
                _MODEL_NAME,
                cache_dir,
            )

            # Try loading from local cache first (offline mode)
            cache_subdir = cache_dir / f"models--{_MODEL_NAME.replace('/', '--')}"
            if cache_subdir.exists():
                # Use the cache dir directly with local_files_only to avoid network calls
                self._model = SentenceTransformer(
                    _MODEL_NAME,
                    cache_folder=str(cache_dir),
                    device="cpu",
                    local_files_only=True,
                )
            else:
                logger.warning("EmbeddingService: model not cached, attempting download...")
                self._model = SentenceTransformer(
                    _MODEL_NAME,
                    cache_folder=str(cache_dir),
                    device="cpu",
                )

            self._loaded = True
            logger.info("EmbeddingService: model loaded successfully (dim=%d)", _EMBEDDING_DIM)
            return True
        except ImportError:
            logger.error(
                "EmbeddingService: 'sentence-transformers' not installed. "
                "Embedding features will be unavailable."
            )
            self._loaded = False
            return False
        except Exception as exc:
            logger.error("EmbeddingService: failed to load model — %s", exc)
            self._loaded = False
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encode_text(self, text: str) -> Optional[list[float]]:
        """Encode a single text string into a 1024-dim vector.

        Returns ``None`` if the model is unavailable.
        """
        if not self._load_model():
            return None
        try:
            embedding = self._model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as exc:
            logger.error("EmbeddingService: encode_text failed — %s", exc)
            return None

    def encode_batch(self, texts: list[str]) -> Optional[list[list[float]]]:
        """Encode a batch of texts into 1024-dim vectors.

        Returns ``None`` if the model is unavailable.
        """
        if not self._load_model():
            return None
        if not texts:
            return []
        try:
            embeddings = self._model.encode(texts, normalize_embeddings=True, batch_size=32)
            return [vec.tolist() for vec in embeddings]
        except Exception as exc:
            logger.error("EmbeddingService: encode_batch failed — %s", exc)
            return None

    @property
    def is_ready(self) -> bool:
        """Whether the model is loaded and ready for inference."""
        return self._loaded and self._model is not None

    @property
    def embedding_dim(self) -> int:
        """Expected embedding dimensionality."""
        return _EMBEDDING_DIM


# ---- Module-level singleton ----
_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Return (and lazily create) the global EmbeddingService instance."""
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service
