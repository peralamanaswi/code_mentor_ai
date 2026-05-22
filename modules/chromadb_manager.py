"""ChromaDB semantic memory for CodeMentor — bugs, code, mentoring, optimizations."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.embedding_service import embed_text, embed_texts, is_embedding_available

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
VECTOR_STORE_PATH = ROOT / "database" / "vector_store"
COLLECTION_NAME = "codementor_memory"

# Chunk settings for long code
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

_client: Optional[Any] = None
_collection: Optional[Any] = None


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_chromadb_available() -> bool:
    """True when chromadb and embeddings are importable."""
    try:
        import chromadb  # noqa: F401
        return is_embedding_available()
    except ImportError:
        return False


def _content_hash(text: str) -> str:
    """Stable hash for deduplication."""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _document_id(topic: str, language: str, filename: str, content: str) -> str:
    """Deterministic ID — upsert prevents duplicate embeddings."""
    raw = f"{topic}|{language}|{filename}|{_content_hash(content)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split long code/text into overlapping chunks for better retrieval."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def get_collection():
    """Return persistent Chroma collection (singleton)."""
    global _client, _collection

    if not is_chromadb_available():
        return None

    if _collection is not None:
        return _collection

    try:
        import chromadb
        from chromadb.config import Settings

        VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(VECTOR_STORE_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        # Cosine space is default for normalized embeddings
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return _collection
    except Exception as exc:
        logger.warning("ChromaDB init failed: %s", exc)
        return None


def upsert_memory(
    content: str,
    *,
    language: str = "auto",
    filename: str = "",
    topic: str = "general",
    error_type: str = "",
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> bool:
    """Store text in Chroma with deduplication via deterministic document IDs.

    Long content is chunked; each chunk gets its own ID derived from chunk hash.
    """
    coll = get_collection()
    if coll is None:
        return False

    chunks = chunk_text(content)
    if not chunks:
        return False

    embeddings = embed_texts(chunks)
    if not embeddings or len(embeddings) != len(chunks):
        logger.warning("Embedding count mismatch; skip Chroma upsert")
        return False

    ids: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    documents: List[str] = []

    for i, chunk in enumerate(chunks):
        doc_id = _document_id(topic, language, filename, chunk)
        meta: Dict[str, Any] = {
            "language": language,
            "filename": filename or "unknown",
            "topic": topic,
            "error_type": error_type or "none",
            "timestamp": _utc_iso(),
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        if metadata_extra:
            meta.update({k: str(v)[:500] for k, v in metadata_extra.items()})

        ids.append(doc_id)
        metadatas.append(meta)
        documents.append(chunk)

    try:
        # upsert = update if id exists → prevents duplicate vectors
        coll.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        return True
    except Exception as exc:
        logger.error("Chroma upsert failed: %s", exc)
        return False


def query_similar(
    query_text: str,
    *,
    n_results: int = 5,
    language: Optional[str] = None,
    topic: Optional[str] = None,
    error_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Cosine similarity search over stored coding memory."""
    coll = get_collection()
    if coll is None or not (query_text or "").strip():
        return []

    query_embedding = embed_text(query_text)
    if not query_embedding:
        return []

    where: Optional[Dict[str, Any]] = None
    filters: List[Dict[str, Any]] = []
    if language:
        filters.append({"language": {"$eq": language}})
    if topic:
        filters.append({"topic": {"$eq": topic}})
    if error_type:
        filters.append({"error_type": {"$eq": error_type}})
    if len(filters) == 1:
        where = filters[0]
    elif len(filters) > 1:
        where = {"$and": filters}

    try:
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = coll.query(**kwargs)
        return _format_query_results(results)
    except Exception as exc:
        logger.warning("Chroma query failed (retry without filter): %s", exc)
        try:
            results = coll.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            return _format_query_results(results)
        except Exception as exc2:
            logger.error("Chroma query retry failed: %s", exc2)
            return []


def retrieve_similar_bugs(error_text: str, language: str = "auto", n: int = 3) -> List[Dict[str, Any]]:
    """Retrieve semantically similar past bug explanations."""
    return query_similar(
        error_text,
        n_results=n,
        language=language if language != "auto" else None,
        topic="bug",
    )


def retrieve_similar_code(code_snippet: str, language: str = "auto", n: int = 3) -> List[Dict[str, Any]]:
    """Retrieve similar uploaded code patterns."""
    return query_similar(
        code_snippet,
        n_results=n,
        language=language if language != "auto" else None,
        topic="code",
    )


def retrieve_mentoring_context(question: str, n: int = 3) -> List[Dict[str, Any]]:
    """Retrieve similar mentor Q&A sessions."""
    return query_similar(question, n_results=n, topic="mentor")


def retrieve_optimization_tips(code: str, language: str = "auto", n: int = 3) -> List[Dict[str, Any]]:
    """Retrieve similar optimization / complexity tips."""
    return query_similar(
        code,
        n_results=n,
        language=language if language != "auto" else None,
        topic="complexity",
    )


def _format_query_results(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten Chroma query response into UI-friendly dicts."""
    formatted: List[Dict[str, Any]] = []
    if not results or not results.get("documents"):
        return formatted

    docs = results["documents"][0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        dist = distances[i] if i < len(distances) else None
        # Chroma cosine distance: lower = more similar
        similarity = round(1 - dist, 3) if dist is not None else None
        formatted.append(
            {
                "document": doc,
                "metadata": meta,
                "similarity": similarity,
            }
        )
    return formatted
