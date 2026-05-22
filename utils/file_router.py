"""Smart file detection and routing to multimodal processors."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from utils.text_extractor import extract_code_from_text, extract_errors_from_text
from utils.validators import get_file_category


@dataclass
class ProcessedFile:
    """Unified result from any uploaded file type."""

    file_type: str
    filename: str
    text: str = ""
    code: str = ""
    error_message: str = ""
    transcript: str = ""
    success: bool = True
    error: Optional[str] = None
    preview_bytes: Optional[bytes] = None
    extra: dict = field(default_factory=dict)


def route_file(uploaded_file) -> ProcessedFile:
    """Detect file type and run the correct processing pipeline.

    Args:
        uploaded_file: Streamlit UploadedFile.

    Returns:
        ProcessedFile with extracted text, code, and errors.
    """
    name = uploaded_file.name or "upload"
    _, ext = os.path.splitext(name.lower())
    category = get_file_category(ext)
    raw_bytes = uploaded_file.getvalue()

    import tempfile

    temp_file_path = None
    result = {}

    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(raw_bytes)
            temp_file_path = tmp.name

        if category == "image":
            from utils.image_processor import process_image
            result = process_image(temp_file_path, name)
        elif category == "pdf":
            from utils.pdf_processor import process_pdf
            result = process_pdf(temp_file_path, name)
        elif category == "document":
            from utils.document_processor import process_document
            result = process_document(temp_file_path, name, ext)
        elif category == "audio":
            from utils.speech_to_text import process_audio
            result = process_audio(temp_file_path, name)
        elif category == "video":
            from utils.video_processor import process_video
            result = process_video(temp_file_path, name)
        elif category == "code":
            result = _process_code_file(temp_file_path, name)
        else:
            return ProcessedFile(
                file_type="unknown",
                filename=name,
                success=False,
                error=f"Unsupported file type: {ext}",
            )
    except Exception as exc:
        return ProcessedFile(
            file_type=category,
            filename=name,
            success=False,
            error=f"Could not process file: {exc}",
        )
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

    text = result.get("text", "") or ""
    code = result.get("code", "") or extract_code_from_text(text)
    if not code and category == "code":
        code = text
    errors = result.get("error_message", "") or extract_errors_from_text(text)

    return ProcessedFile(
        file_type=category,
        filename=name,
        text=text,
        code=code,
        error_message=errors,
        transcript=result.get("transcript", "") or "",
        success=result.get("success", True),
        error=result.get("error"),
        preview_bytes=raw_bytes if category in ("image", "audio", "video") else None,
        extra=result,
    )


def _process_code_file(file_path: str, name: str) -> dict[str, Any]:
    """Read plain code file bytes as text."""
    text = ""
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                text = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
    except Exception as exc:
        return {
            "text": "",
            "code": "",
            "success": False,
            "error": f"Failed to read code file: {exc}",
        }
    return {
        "text": text,
        "code": text,
        "success": bool(text.strip()),
        "error": None if text.strip() else "Empty code file.",
    }
