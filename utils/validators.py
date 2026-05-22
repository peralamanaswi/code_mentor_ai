"""Input validation for code, files, and multimodal uploads."""

from __future__ import annotations

import os
from typing import Optional, Tuple

# Performance limits
MAX_FILE_SIZE_BYTES: int = 1 * 1024 * 1024  # 1 MB – code, docs, images
MAX_MEDIA_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB – audio/video
MAX_CODE_CHARS: int = 50_000

# Legacy code-only extensions (backward compatible)
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".java", ".cpp", ".js", ".txt", ".c",
})

# Full multimodal support
IMAGE_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})
DOCUMENT_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".txt"})
AUDIO_EXTENSIONS: frozenset[str] = frozenset({".mp3", ".wav", ".m4a"})
VIDEO_EXTENSIONS: frozenset[str] = frozenset({".mp4", ".mov"})
CODE_EXTENSIONS: frozenset[str] = frozenset({".py", ".java", ".cpp", ".js", ".c", ".txt"})

MULTIMODAL_EXTENSIONS: frozenset[str] = (
    IMAGE_EXTENSIONS
    | DOCUMENT_EXTENSIONS
    | AUDIO_EXTENSIONS
    | VIDEO_EXTENSIONS
    | CODE_EXTENSIONS
)

MEDIA_EXTENSIONS: frozenset[str] = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

# Streamlit file_uploader type list (no leading dot)
UPLOAD_TYPE_LABELS: list[str] = sorted(
    ext.lstrip(".") for ext in MULTIMODAL_EXTENSIONS
)


def get_file_category(ext: str) -> str:
    """Return category: image, pdf, document, audio, video, code, unknown."""
    ext = ext.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext == ".pdf":
        return "pdf"
    if ext in (".docx", ".txt"):
        return "document"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in {".py", ".java", ".cpp", ".js", ".c"}:
        return "code"
    return "unknown"


def validate_code_input(code: str) -> Tuple[bool, Optional[str]]:
    """Validate pasted code length and non-empty content."""
    stripped = (code or "").strip()
    if not stripped:
        return False, "Please paste your code or upload a file before continuing."
    if len(code) > MAX_CODE_CHARS:
        return (
            False,
            f"Your code is too long ({len(code):,} characters). "
            f"Maximum allowed is {MAX_CODE_CHARS:,} characters.",
        )
    return True, None


def validate_error_message(error_msg: str, required: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate optional or required error message field."""
    if required and not (error_msg or "").strip():
        return False, "Please paste the error message you received when running your code."
    if error_msg and len(error_msg) > 10_000:
        return False, "Error message is too long. Please paste only the relevant error part."
    return True, None


def validate_uploaded_file(
    uploaded_file,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate file for legacy code-only uploaders."""
    if uploaded_file is None:
        return True, None, None
    return validate_multimodal_file(uploaded_file, code_only=True)


def validate_multimodal_file(
    uploaded_file,
    code_only: bool = False,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate multimodal upload size and extension."""
    if uploaded_file is None:
        return True, None, None

    name = uploaded_file.name or ""
    _, ext = os.path.splitext(name.lower())
    allowed = ALLOWED_EXTENSIONS if code_only else MULTIMODAL_EXTENSIONS

    if ext not in allowed:
        return (
            False,
            f"File type '{ext or 'unknown'}' is not supported. "
            f"Allowed: {', '.join(sorted(allowed))}",
            None,
        )

    try:
        data = uploaded_file.getvalue()
    except Exception:
        return False, "Could not read the uploaded file. Please try again.", None

    max_size = MAX_MEDIA_SIZE_BYTES if ext in MEDIA_EXTENSIONS else MAX_FILE_SIZE_BYTES
    if len(data) > max_size:
        limit_mb = max_size / (1024 * 1024)
        return (
            False,
            f"File is too large ({len(data) / 1024:.1f} KB). Maximum is {limit_mb:.0f} MB.",
            None,
        )

    return True, None, ext


def validate_analysis_input(code: str, error_msg: str = "") -> Tuple[bool, Optional[str]]:
    """Validate that there is code and/or error/transcript to analyze."""
    if (code or "").strip() or (error_msg or "").strip():
        combined = f"{code}{error_msg}"
        if len(combined) > MAX_CODE_CHARS:
            return False, f"Combined input too long. Max {MAX_CODE_CHARS:,} characters."
        return True, None
    return False, "Please paste code, an error message, or upload a supported file."


def merge_code_inputs(pasted: str, file_content: Optional[str]) -> str:
    """Prefer file content when both paste and upload exist."""
    if file_content and file_content.strip():
        return file_content
    return pasted or ""
