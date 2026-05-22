"""Unified AI client: Groq primary, Gemini fallback, retry logic."""

from __future__ import annotations

import logging
import os
import time
import streamlit as st
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_TIMEOUT_SEC = 30
GEMINI_TIMEOUT_SEC = 45
GROQ_MAX_RETRIES = 2

GROQ_MODELS: List[str] = [
    "llama-3.3-70b-versatile",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
]

GEMINI_MODEL = "gemini-2.5-flash"


class AIResponseError(Exception):
    """Raised when all AI providers fail."""


def _get_groq_client():
    """Create Groq client if API key exists."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        return None, None
    try:
        from groq import Groq

        return Groq(api_key=api_key), api_key
    except Exception as exc:
        logger.warning("Groq client init failed: %s", exc)
        return None, None


def _call_groq(prompt: str) -> Optional[str]:
    """Call Groq API with model fallback chain.

    Args:
        prompt: User/system prompt.

    Returns:
        Response text or None on failure.
    """
    client, _ = _get_groq_client()
    if client is None:
        return None

    last_error: Optional[Exception] = None
    for model in GROQ_MODELS:
        for attempt in range(GROQ_MAX_RETRIES + 1):
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are CodeMentor AI, a patient tutor for beginner "
                                "programmers. Use clear, simple English."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=4096,
                    timeout=GROQ_TIMEOUT_SEC,
                )
                text = completion.choices[0].message.content
                if text:
                    return text.strip()
            except Exception as exc:
                last_error = exc
                err_str = str(exc).lower()
                if "rate" in err_str or "429" in err_str:
                    time.sleep(2 ** attempt)
                if attempt < GROQ_MAX_RETRIES:
                    time.sleep(1)
                logger.warning("Groq attempt %s model %s: %s", attempt, model, exc)
    if last_error:
        logger.error("Groq failed: %s", last_error)
    return None


def _call_gemini(prompt: str) -> Optional[str]:
    """Call Google Gemini as fallback.

    Args:
        prompt: Full prompt text.

    Returns:
        Response text or None.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 4096,
            },
        )
        if response:
            try:
                text = response.text
            except (ValueError, AttributeError):
                text = None
                if getattr(response, "candidates", None):
                    parts = response.candidates[0].content.parts
                    text = "".join(getattr(p, "text", "") for p in parts)
            if text:
                return text.strip()
    except Exception as exc:
        logger.error("Gemini failed: %s", exc)
    return None


def generate_ai_response(prompt: str, use_cache: bool = True) -> Optional[str]:
    """Generate AI response with Groq → retry → Gemini fallback.

    Gen AI: Prompt Engineering (caller builds prompt), NLG (model output),
    Structured reasoning via prompt format in templates.

    Args:
        prompt: Complete prompt string.
        use_cache: Whether to use Streamlit cache (avoid in cache wrapper).

    Returns:
        AI text or None if all providers fail.
    """
    if use_cache:
        from utils.cache_manager import cached_ai_response, make_cache_key

        key = make_cache_key("ai", prompt[:2000], "")
        return cached_ai_response(prompt, key)

    # Try Groq with retries (handled inside _call_groq)
    result = _call_groq(prompt)
    if result:
        return result

    # Fallback to Gemini
    result = _call_gemini(prompt)
    return result


def is_ai_available() -> bool:
    """Check if at least one API key is configured.

    Returns:
        True if Groq or Gemini key is set via environment variables or via the
        custom key inputs in the Streamlit sidebar.
    """
    # Prefer custom keys entered by the user during the session
    custom_groq = st.session_state.get("custom_groq_key", "").strip()
    custom_gemini = st.session_state.get("custom_gemini_key", "").strip()
    if custom_groq and not custom_groq.startswith("your_"):
        return True
    if custom_gemini and not custom_gemini.startswith("your_"):
        return True
    # Fallback to environment variables
    groq = os.getenv("GROQ_API_KEY", "").strip()
    gemini = os.getenv("GEMINI_API_KEY", "").strip()
    valid = lambda k: k and not k.startswith("your_")
    return valid(groq) or valid(gemini)
