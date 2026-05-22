"""Streamlit caching for expensive AI and analysis calls."""

from __future__ import annotations

import hashlib
from typing import Optional

import streamlit as st


def _hash_key(*parts: str) -> str:
    """Create stable cache key from string parts."""
    combined = "||".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:32]


@st.cache_data(ttl=3600, show_spinner=False)
def cached_ai_response(prompt: str, cache_key: str) -> Optional[str]:
    """Cache AI responses by prompt hash to reduce API calls.

    Args:
        prompt: Full prompt sent to LLM.
        cache_key: Unique key for this request type.

    Returns:
        AI response text or None.
    """
    from modules.ai_response import generate_ai_response

    return generate_ai_response(prompt, use_cache=False)


def make_cache_key(feature: str, code: str, extra: str = "") -> str:
    """Build cache key for a feature run.

    Args:
        feature: Feature name e.g. 'bug_explainer'.
        code: Source code.
        extra: Additional context (error msg, language, etc.).

    Returns:
        Short hash string.
    """
    return _hash_key(feature, code[:5000], extra)
