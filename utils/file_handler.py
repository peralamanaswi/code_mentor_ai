"""File upload and report download helpers."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.validators import ALLOWED_EXTENSIONS, MULTIMODAL_EXTENSIONS

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "analysis_reports"


def read_uploaded_file(uploaded_file) -> tuple[Optional[str], Optional[str]]:
    """Read text content from a Streamlit uploaded file.

    Args:
        uploaded_file: Streamlit UploadedFile.

    Returns:
        Tuple of (content, error_message).
    """
    if uploaded_file is None:
        return None, None

    try:
        raw = uploaded_file.getvalue()
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return raw.decode(encoding), None
            except UnicodeDecodeError:
                continue
        return None, "Could not decode file. Please save as UTF-8 text and try again."
    except Exception as exc:
        return None, f"Failed to read file: {exc}"


def get_file_extension(filename: str) -> str:
    """Return lowercase extension including dot.

    Args:
        filename: Original filename.

    Returns:
        Extension like '.py' or empty string.
    """
    name = (filename or "").lower()
    for ext in sorted(MULTIMODAL_EXTENSIONS | ALLOWED_EXTENSIONS, key=len, reverse=True):
        if name.endswith(ext):
            return ext
    return Path(name).suffix.lower()


def save_report_to_disk(report_text: str, prefix: str = "codementor_report") -> Path:
    """Persist report for optional archival (session-local use).

    Args:
        report_text: Full report body.
        prefix: Filename prefix.

    Returns:
        Path to saved file.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"{prefix}_{timestamp}.txt"
    path.write_text(report_text, encoding="utf-8")
    return path


def report_download_buffer(report_text: str) -> io.BytesIO:
    """Create in-memory buffer for Streamlit download button.

    Args:
        report_text: Report content.

    Returns:
        BytesIO ready for st.download_button.
    """
    buffer = io.BytesIO(report_text.encode("utf-8"))
    buffer.seek(0)
    return buffer
