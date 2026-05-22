"""Sentence-transformer embedding service for ChromaDB semantic search."""

from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
_model: Optional[object] = None
_model_load_error: Optional[str] = None


def is_embedding_available() -> bool:
    """Check if sentence-transformers can be loaded."""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def get_embedding_model():
    """Lazy-load the MiniLM model (cached in process memory)."""
    global _model, _model_load_error

    if _model is not None:
        return _model
    if _model_load_error:
        return None

    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Loaded embedding model: %s", MODEL_NAME)
        return _model
    except Exception as exc:
        _model_load_error = str(exc)
        logger.warning("Embedding model load failed: %s", exc)
        return None


def embed_text(text: str) -> Optional[List[float]]:
    """Embed a single text string; returns normalized vector or None."""
    vectors = embed_texts([text])
    return vectors[0] if vectors else None


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed multiple texts with cosine-friendly normalization.

    Args:
        texts: Non-empty strings to embed.

    Returns:
        List of embedding vectors (empty if model unavailable).
    """
    if not texts:
        return []

    model = get_embedding_model()
    if model is None:
        return []

    try:
        # normalize_embeddings=True → unit vectors for cosine similarity in Chroma
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [emb.tolist() for emb in embeddings]
    except Exception as exc:
        logger.error("embed_texts failed: %s", exc)
        return []
