"""Backward-compatible interview storage — delegates to modules.mongodb."""

from __future__ import annotations

from typing import Any, Dict

from modules.mongodb import insert_interview_record, is_mongodb_available

__all__ = ["save_interview_record", "is_mongodb_configured"]


def is_mongodb_configured() -> bool:
    """True when MONGODB_URI (or MONGO_URI) is set."""
    return is_mongodb_available()


def save_interview_record(record: Dict[str, Any]) -> None:
    """Persist interview evaluation via centralized MongoDB module."""
    if not is_mongodb_available():
        raise RuntimeError(
            "MongoDB not configured. Set MONGODB_URI in your .env file."
        )
    inserted = insert_interview_record(record)
    if inserted is None:
        raise RuntimeError("Failed to save interview record to MongoDB.")
