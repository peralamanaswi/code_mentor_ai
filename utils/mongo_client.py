'''MongoDB client utilities for storing interview data'''

import os
import streamlit as st

try:
    from pymongo import MongoClient
except ImportError:  # pragma: no cover
    MongoClient = None

__all__ = ["save_interview_record"]


def _get_collection():
    """Return a MongoDB collection for interview records.

    The MongoDB connection URI is taken from the Streamlit session state key
    ``custom_mongo_uri`` (entered by the user in the sidebar) or from the
    environment variable ``MONGO_URI``. The database name defaults to
    ``interview_db`` (or ``MONGO_DB`` env var) and the collection name is
    ``interviews``.

    Raises:
        RuntimeError: If no URI is provided or ``pymongo`` is not installed.
    """
    if MongoClient is None:
        raise RuntimeError("pymongo is not installed. Install it to enable MongoDB storage.")

    uri = st.session_state.get("custom_mongo_uri", "").strip() or os.getenv("MONGO_URI", "").strip()
    if not uri:
        raise RuntimeError("MongoDB URI not provided. Set it via the sidebar or MONGO_URI env var.")

    # Create client with a short timeout to avoid hanging the UI.
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    # Verify connection quickly.
    try:
        client.admin.command("ping")
    except Exception as exc:
        raise RuntimeError(f"Failed to connect to MongoDB: {exc}")

    db_name = os.getenv("MONGO_DB", "interview_db")
    db = client[db_name]
    collection = db["interviews"]
    return collection


def save_interview_record(record: dict) -> None:
    """Persist an interview *record* to MongoDB.

    The *record* should be a flat dictionary containing at least the keys
    ``language``, ``difficulty``, ``question``, ``answer``, ``score`` and
    ``timestamp``. Additional fields are allowed.
    """
    coll = _get_collection()
    # ``insert_one`` returns an InsertOneResult; we ignore it here.
    coll.insert_one(record)
