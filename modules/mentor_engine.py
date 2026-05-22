"""AI mentor orchestration: MongoDB + ChromaDB + context-aware LLM responses."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from modules.ai_response import generate_ai_response, is_ai_available
from modules.chromadb_manager import (
    is_chromadb_available,
    retrieve_mentoring_context,
    retrieve_optimization_tips,
    retrieve_similar_bugs,
    retrieve_similar_code,
    upsert_memory,
)
from modules.code_analyzer import (
    build_retrieval_query,
    parse_bug_report,
    parse_complexity_report,
)
from modules.mongodb import (
    insert_bug_result,
    insert_code_history,
    insert_complexity_result,
    insert_mentor_history,
    insert_user_query,
    is_mongodb_available,
)
from utils.prompt_templates import context_retrieval_prompt

logger = logging.getLogger(__name__)


def backend_status() -> Dict[str, bool]:
    """Report which persistence layers are active."""
    return {
        "mongodb": is_mongodb_available(),
        "chromadb": is_chromadb_available(),
    }


def record_code_upload(code: str, language: str, filename: str = "") -> None:
    """Step 1 of pipeline — persist code snapshot to MongoDB."""
    if not code.strip():
        return
    try:
        insert_code_history(filename or "pasted_code", code, language)
    except Exception as exc:
        logger.warning("record_code_upload: %s", exc)


def record_user_query(query: str, language: str, module: str) -> None:
    """Log user intent before analysis."""
    if not query.strip():
        return
    try:
        insert_user_query(query, language, module)
    except Exception as exc:
        logger.warning("record_user_query: %s", exc)


def retrieve_context(
    code: str,
    error_msg: str,
    feature: str,
    language: str = "auto",
) -> Tuple[str, List[Dict[str, Any]]]:
    """Semantic retrieval from ChromaDB for similar bugs, code, and mentor memory."""
    if not is_chromadb_available():
        return "", []

    query = build_retrieval_query(code, error_msg, feature)
    hits: List[Dict[str, Any]] = []

    if feature in ("bug", "full"):
        hits.extend(retrieve_similar_bugs(query, language=language, n=3))
    if feature in ("bug", "complexity", "security", "full"):
        hits.extend(retrieve_similar_code(code, language=language, n=2))
    if feature in ("complexity", "full"):
        hits.extend(retrieve_optimization_tips(code, language=language, n=2))
    if feature in ("interview", "mentor", "full"):
        hits.extend(retrieve_mentoring_context(query, n=2))

    # Deduplicate by document text
    seen = set()
    unique: List[Dict[str, Any]] = []
    for h in hits:
        doc = h.get("document", "")
        if doc and doc not in seen:
            seen.add(doc)
            unique.append(h)
    unique = unique[:6]

    context_block = context_retrieval_prompt(unique)
    return context_block, unique


def build_contextual_prompt(
    base_prompt: str,
    code: str,
    error_msg: str,
    feature: str,
    language: str = "auto",
) -> str:
    """Inject ChromaDB-retrieved context into the LLM prompt."""
    context_block, _ = retrieve_context(code, error_msg, feature, language)
    if context_block:
        return f"{context_block}\n\n---\n\n{base_prompt}"
    return base_prompt


def generate_mentor_response(
    base_prompt: str,
    *,
    code: str = "",
    error_msg: str = "",
    feature: str = "mentor",
    language: str = "auto",
    filename: str = "",
    user_question: str = "",
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """Full pipeline: log query → retrieve context → AI response → persist memory.

    Flow:
        User Input → record query/code → Chroma retrieval → prompt injection → LLM
    """
    # MongoDB: user query + code history (non-blocking)
    record_user_query(user_question or error_msg or code[:200], language, feature)
    record_code_upload(code, language, filename)

    context_block, hits = retrieve_context(code, error_msg, feature, language)
    prompt = base_prompt
    if context_block:
        prompt = f"{context_block}\n\n---\n\n{base_prompt}"

    if not is_ai_available():
        return None, hits

    response = generate_ai_response(prompt)
    return response, hits


def persist_bug_session(
    code: str,
    error_msg: str,
    report: str,
    language: str,
    filename: str = "",
) -> None:
    """Save bug results to MongoDB and ChromaDB after analysis."""
    parsed = parse_bug_report(report, error_msg, code)
    try:
        insert_bug_result(
            detected_errors=parsed["detected_errors"],
            explanation=parsed["explanation"],
            fixed_code=parsed["fixed_code"],
            confidence_score=float(parsed["confidence_score"]),
            language=language,
            filename=filename,
        )
    except Exception as exc:
        logger.warning("persist_bug_session mongo: %s", exc)

    # Chroma: store explanation + code for future similarity
    memory_text = f"Error: {error_msg}\n\nExplanation:\n{parsed['explanation']}\n\nCode:\n{code[:2000]}"
    upsert_memory(
        memory_text,
        language=language,
        filename=filename,
        topic="bug",
        error_type=parsed.get("error_type", "general"),
    )
    if code.strip():
        upsert_memory(code, language=language, filename=filename, topic="code")


def persist_complexity_session(
    code: str,
    report: str,
    static_report: str,
    language: str,
    filename: str = "",
) -> None:
    """Save complexity metrics to MongoDB and optimization tips to Chroma."""
    parsed = parse_complexity_report(report, static_report)
    try:
        insert_complexity_result(
            cyclomatic_complexity=parsed["cyclomatic_complexity"],
            readability_score=parsed["readability_score"],
            optimization_tips=parsed["optimization_tips"],
            language=language,
            filename=filename,
            full_report=report[:50_000],
        )
    except Exception as exc:
        logger.warning("persist_complexity_session mongo: %s", exc)

    tips_text = f"{parsed['optimization_tips']}\n\n{report[:3000]}"
    upsert_memory(
        tips_text,
        language=language,
        filename=filename,
        topic="complexity",
    )
    if code.strip():
        upsert_memory(code, language=language, filename=filename, topic="code")


def persist_mentor_session(
    user_question: str,
    ai_response: str,
    module: str,
    language: str = "auto",
    feedback: str = "",
) -> None:
    """Save Q&A to MongoDB and Chroma mentor topic."""
    try:
        insert_mentor_history(user_question, ai_response, feedback, module, language)
    except Exception as exc:
        logger.warning("persist_mentor_session mongo: %s", exc)

    combined = f"Q: {user_question}\n\nA: {ai_response[:4000]}"
    upsert_memory(combined, language=language, topic="mentor", filename=module)


def persist_security_session(code: str, report: str, language: str = "python") -> None:
    """Store security mentoring in vector memory."""
    upsert_memory(
        f"Security analysis:\n{report[:4000]}\n\nCode:\n{code[:1500]}",
        language=language,
        topic="security",
    )
    persist_mentor_session(
        user_question=f"Security scan on {len(code)} chars of code",
        ai_response=report,
        module="security",
        language=language,
    )


def persist_full_session(
    code: str,
    error_msg: str,
    report: str,
    language: str,
    filename: str = "",
) -> None:
    """Persist combined analysis across bug + complexity + security topics."""
    persist_bug_session(code, error_msg, report, language, filename)
    persist_complexity_session(code, report, "", language, filename)
    upsert_memory(
        report[:5000],
        language=language,
        filename=filename,
        topic="full_analysis",
    )
