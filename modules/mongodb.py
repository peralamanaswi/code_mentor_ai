"""MongoDB persistence layer for CodeMentor AI.

Stores user queries, code uploads, bug results, complexity analysis,
and AI mentor conversation history. Connection uses MONGODB_URI (or MONGO_URI).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database
except ImportError:  # pragma: no cover
    MongoClient = None  # type: ignore[misc, assignment]
    Collection = None  # type: ignore[misc, assignment]
    Database = None  # type: ignore[misc, assignment]

# Collection names — one per data domain
COL_USER_QUERIES = "user_queries"
COL_CODE_HISTORY = "code_history"
COL_BUG_RESULTS = "bug_results"
COL_COMPLEXITY_RESULTS = "complexity_results"
COL_MENTOR_HISTORY = "mentor_history"
COL_INTERVIEWS = "interviews"  # backward compatibility

_client: Optional[Any] = None
_db: Optional[Any] = None


def _utc_now() -> datetime:
    """Timezone-aware timestamp for all records."""
    return datetime.now(timezone.utc)


def get_mongodb_uri() -> str:
    """Read URI from env; supports legacy MONGO_URI."""
    return (
        os.getenv("MONGODB_URI", "").strip()
        or os.getenv("MONGO_URI", "").strip()
    )


def is_mongodb_available() -> bool:
    """True when pymongo is installed and a URI is configured."""
    if MongoClient is None:
        return False
    uri = get_mongodb_uri()
    return bool(uri and not uri.startswith("your_"))


def get_database() -> Optional[Database]:
    """Return cached database handle or None if unavailable."""
    global _client, _db

    if not is_mongodb_available():
        return None

    if _db is not None:
        return _db

    try:
        uri = get_mongodb_uri()
        # Short timeouts so Streamlit sidebar/history never hangs on bad network
        _client = MongoClient(
            uri,
            serverSelectionTimeoutMS=4000,
            connectTimeoutMS=4000,
            socketTimeoutMS=10000,
        )
        _client.admin.command("ping")
        db_name = os.getenv("MONGODB_DB", os.getenv("MONGO_DB", "codementor_ai"))
        _db = _client[db_name]
        return _db
    except Exception as exc:
        logger.warning("MongoDB connection failed: %s", exc)
        _client = None
        _db = None
        return None


def _collection(name: str) -> Optional[Collection]:
    """Get a collection handle; None if DB is offline."""
    db = get_database()
    if db is None:
        return None
    return db[name]


def _safe_insert(collection_name: str, document: Dict[str, Any]) -> Optional[str]:
    """Insert document with timestamp; returns inserted id string or None."""
    coll = _collection(collection_name)
    if coll is None:
        return None
    doc = dict(document)
    if "timestamp" not in doc:
        doc["timestamp"] = _utc_now()
    try:
        result = coll.insert_one(doc)
        return str(result.inserted_id)
    except Exception as exc:
        logger.error("MongoDB insert into %s failed: %s", collection_name, exc)
        return None


# ---------------------------------------------------------------------------
# A. User Queries
# ---------------------------------------------------------------------------

def insert_user_query(
    user_query: str,
    programming_language: str = "auto",
    module: str = "general",
) -> Optional[str]:
    """Store a user query before AI processing."""
    return _safe_insert(
        COL_USER_QUERIES,
        {
            "user_query": user_query,
            "programming_language": programming_language,
            "module": module,
        },
    )


def fetch_user_queries(limit: int = 50, language: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch recent user queries, newest first."""
    coll = _collection(COL_USER_QUERIES)
    if coll is None:
        return []
    query: Dict[str, Any] = {}
    if language:
        query["programming_language"] = language
    try:
        cursor = coll.find(query).sort("timestamp", -1).limit(limit)
        return [_serialize_doc(d) for d in cursor]
    except Exception as exc:
        logger.error("fetch_user_queries failed: %s", exc)
        return []


def search_user_queries(keyword: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Text search on user_query field."""
    coll = _collection(COL_USER_QUERIES)
    if coll is None:
        return []
    try:
        cursor = coll.find(
            {"user_query": {"$regex": keyword, "$options": "i"}},
        ).sort("timestamp", -1).limit(limit)
        return [_serialize_doc(d) for d in cursor]
    except Exception as exc:
        logger.error("search_user_queries failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# B. Uploaded Code History
# ---------------------------------------------------------------------------

def insert_code_history(
    filename: str,
    code_content: str,
    language: str,
) -> Optional[str]:
    """Store uploaded or pasted code snapshot."""
    return _safe_insert(
        COL_CODE_HISTORY,
        {
            "filename": filename or "pasted_code",
            "code_content": code_content[:100_000],
            "language": language,
            "upload_time": _utc_now(),
        },
    )


def fetch_code_history(limit: int = 50, language: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch recent code uploads."""
    coll = _collection(COL_CODE_HISTORY)
    if coll is None:
        return []
    query: Dict[str, Any] = {}
    if language:
        query["language"] = language
    try:
        cursor = coll.find(query).sort("upload_time", -1).limit(limit)
        return [_serialize_doc(d) for d in cursor]
    except Exception as exc:
        logger.error("fetch_code_history failed: %s", exc)
        return []


def search_code_history(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search code content or filename."""
    coll = _collection(COL_CODE_HISTORY)
    if coll is None:
        return []
    try:
        cursor = coll.find(
            {
                "$or": [
                    {"code_content": {"$regex": keyword, "$options": "i"}},
                    {"filename": {"$regex": keyword, "$options": "i"}},
                ]
            },
        ).sort("upload_time", -1).limit(limit)
        return [_serialize_doc(d) for d in cursor]
    except Exception as exc:
        logger.error("search_code_history failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# C. Bug Detection Results
# ---------------------------------------------------------------------------

def insert_bug_result(
    detected_errors: str,
    explanation: str,
    fixed_code: str,
    confidence_score: float,
    language: str = "auto",
    filename: str = "",
) -> Optional[str]:
    """Persist bug analysis outcome."""
    return _safe_insert(
        COL_BUG_RESULTS,
        {
            "detected_errors": detected_errors,
            "explanation": explanation[:20_000],
            "fixed_code": fixed_code[:50_000],
            "confidence_score": confidence_score,
            "language": language,
            "filename": filename,
        },
    )


def fetch_bug_results(limit: int = 50, language: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch recent bug debugging sessions."""
    coll = _collection(COL_BUG_RESULTS)
    if coll is None:
        return []
    query: Dict[str, Any] = {}
    if language:
        query["language"] = language
    try:
        cursor = coll.find(query).sort("timestamp", -1).limit(limit)
        return [_serialize_doc(d) for d in cursor]
    except Exception as exc:
        logger.error("fetch_bug_results failed: %s", exc)
        return []


def search_bug_results(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search bugs by error text or explanation."""
    coll = _collection(COL_BUG_RESULTS)
    if coll is None:
        return []
    try:
        cursor = coll.find(
            {
                "$or": [
                    {"detected_errors": {"$regex": keyword, "$options": "i"}},
                    {"explanation": {"$regex": keyword, "$options": "i"}},
                ]
            },
        ).sort("timestamp", -1).limit(limit)
        return [_serialize_doc(d) for d in cursor]
    except Exception as exc:
        logger.error("search_bug_results failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# D. Complexity Analysis
# ---------------------------------------------------------------------------

def insert_complexity_result(
    cyclomatic_complexity: str,
    readability_score: str,
    optimization_tips: str,
    language: str = "auto",
    filename: str = "",
    full_report: str = "",
) -> Optional[str]:
    """Persist complexity analysis metrics."""
    return _safe_insert(
        COL_COMPLEXITY_RESULTS,
        {
            "cyclomatic_complexity": cyclomatic_complexity,
            "readability_score": readability_score,
            "optimization_tips": optimization_tips[:20_000],
            "language": language,
            "filename": filename,
            "full_report": full_report[:50_000],
        },
    )


def fetch_complexity_results(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent complexity analyses."""
    coll = _collection(COL_COMPLEXITY_RESULTS)
    if coll is None:
        return []
    try:
        cursor = coll.find().sort("timestamp", -1).limit(limit)
        return [_serialize_doc(d) for d in cursor]
    except Exception as exc:
        logger.error("fetch_complexity_results failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# E. AI Mentor History
# ---------------------------------------------------------------------------

def insert_mentor_history(
    user_question: str,
    ai_response: str,
    feedback: str = "",
    module: str = "mentor",
    language: str = "auto",
) -> Optional[str]:
    """Store Q&A mentor exchange."""
    return _safe_insert(
        COL_MENTOR_HISTORY,
        {
            "user_question": user_question[:10_000],
            "ai_response": ai_response[:50_000],
            "feedback": feedback,
            "module": module,
            "language": language,
        },
    )


def fetch_mentor_history(limit: int = 50, module: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch mentor conversation history."""
    coll = _collection(COL_MENTOR_HISTORY)
    if coll is None:
        return []
    query: Dict[str, Any] = {}
    if module:
        query["module"] = module
    try:
        cursor = coll.find(query).sort("timestamp", -1).limit(limit)
        return [_serialize_doc(d) for d in cursor]
    except Exception as exc:
        logger.error("fetch_mentor_history failed: %s", exc)
        return []


def search_mentor_history(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search mentor Q&A by question or response text."""
    coll = _collection(COL_MENTOR_HISTORY)
    if coll is None:
        return []
    try:
        cursor = coll.find(
            {
                "$or": [
                    {"user_question": {"$regex": keyword, "$options": "i"}},
                    {"ai_response": {"$regex": keyword, "$options": "i"}},
                ]
            },
        ).sort("timestamp", -1).limit(limit)
        return [_serialize_doc(d) for d in cursor]
    except Exception as exc:
        logger.error("search_mentor_history failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Interview records (legacy utils/mongo_client.py compatibility)
# ---------------------------------------------------------------------------

def insert_interview_record(record: Dict[str, Any]) -> Optional[str]:
    """Save interview evaluation to interviews collection."""
    coll = _collection(COL_INTERVIEWS)
    if coll is None:
        return None
    doc = dict(record)
    if "timestamp" not in doc:
        doc["timestamp"] = _utc_now()
    try:
        result = coll.insert_one(doc)
        return str(result.inserted_id)
    except Exception as exc:
        logger.error("insert_interview_record failed: %s", exc)
        return None


def fetch_all_history_summary() -> Dict[str, int]:
    """Count documents per collection for History dashboard."""
    counts = {
        "user_queries": 0,
        "code_history": 0,
        "bug_results": 0,
        "complexity_results": 0,
        "mentor_history": 0,
        "interviews": 0,
    }
    mapping = {
        "user_queries": COL_USER_QUERIES,
        "code_history": COL_CODE_HISTORY,
        "bug_results": COL_BUG_RESULTS,
        "complexity_results": COL_COMPLEXITY_RESULTS,
        "mentor_history": COL_MENTOR_HISTORY,
        "interviews": COL_INTERVIEWS,
    }
    db = get_database()
    if db is None:
        return counts
    for key, col_name in mapping.items():
        try:
            counts[key] = db[col_name].estimated_document_count()
        except Exception:
            counts[key] = 0
    return counts


def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert ObjectId and datetime for JSON/UI display."""
    out = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    for key in ("timestamp", "upload_time"):
        if key in out and hasattr(out[key], "isoformat"):
            out[key] = out[key].isoformat()
    return out
