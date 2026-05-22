"""Shared Streamlit multimodal upload, preview, and input merging."""

from __future__ import annotations

from typing import Optional, Tuple

import streamlit as st

from utils.file_router import ProcessedFile, route_file
from utils.validators import UPLOAD_TYPE_LABELS, merge_code_inputs, validate_multimodal_file


def render_multimodal_uploader(key_prefix: str, label: str | None = None) -> Tuple[Optional[object], Optional[ProcessedFile]]:
    """ChatGPT-style drag-and-drop uploader with auto processing.

    Args:
        key_prefix: Unique key prefix per page.
        label: Optional uploader label.

    Returns:
        Tuple of (uploaded_file, ProcessedFile or None).
    """
    uploader_label = label or "📎 Upload photos & files"
    st.caption("Supports images, PDF, DOCX, TXT, audio, video, and code files.")

    uploaded = st.file_uploader(
        uploader_label,
        type=UPLOAD_TYPE_LABELS,
        key=f"{key_prefix}_mm_upload",
        help="Drag and drop or click to browse. Max 1MB (docs/images/code), 10MB (audio/video).",
    )

    if uploaded is None:
        return None, None

    valid, err, _ = validate_multimodal_file(uploaded)
    if not valid:
        st.error(err)
        return uploaded, None

    processed: Optional[ProcessedFile] = None
    import logging
    logger = logging.getLogger(__name__)

    try:
        with st.spinner("Extracting content..."):
            processed = route_file(uploaded)
    except Exception as exc:
        logger.exception("Exception during file routing/processing for %s: %s", uploaded.name, exc)
        st.error("Unable to extract content from this file. Please try another file.")
        return uploaded, None

    if processed and not processed.success:
        logger.error("Failed to extract content from %s. Error: %s", processed.filename, processed.error)
        st.error("Unable to extract content from this file. Please try another file.")
        return uploaded, None

    if processed:
        render_file_preview(uploaded, processed)

    return uploaded, processed


def render_file_preview(uploaded_file, processed: ProcessedFile) -> None:
    """Show preview based on detected file type."""
    st.write(f"Detected File Type: {processed.file_type}")
    st.write("Preview Section:")
    st.write("Extracted Text")

    ft = processed.file_type
    raw = uploaded_file.getvalue()

    with st.expander("📁 File preview", expanded=True):
        if ft == "image":
            st.image(raw, caption="Uploaded image", use_container_width=True)
            st.text_area("Extracted Text Preview", processed.text, height=200, disabled=True, key=f"img_prev_{processed.filename}")

        elif ft == "pdf":
            st.text_area("Extracted Text Preview", processed.text, height=200, disabled=True, key=f"pdf_prev_{processed.filename}")

        elif ft == "document":
            st.text_area("Extracted Text Preview", processed.text, height=200, disabled=True, key=f"doc_prev_{processed.filename}")

        elif ft == "audio":
            st.audio(raw)
            st.text_area("Extracted Text Preview", processed.transcript or processed.text, height=200, disabled=True, key=f"aud_prev_{processed.filename}")

        elif ft == "video":
            st.video(raw)
            st.text_area("Extracted Text Preview", processed.text, height=200, disabled=True, key=f"vid_prev_{processed.filename}")

        elif ft == "code":
            st.text_area("Extracted Text Preview", processed.code or processed.text, height=200, disabled=True, key=f"code_prev_{processed.filename}")

        if processed.code and ft != "code":
            st.markdown("**Extracted code:**")
            st.code(processed.code[:3000], language="python")

        if processed.error_message:
            st.markdown("**Detected errors:**")
            st.warning(processed.error_message[:1500])


def merge_multimodal_inputs(
    pasted_code: str,
    pasted_error: str,
    processed: Optional[ProcessedFile],
) -> Tuple[str, str, str]:
    """Merge paste fields with processed multimodal content.

    Returns:
        Tuple of (code, error_message, filename).
    """
    if processed is None:
        return (pasted_code or "").strip(), (pasted_error or "").strip(), ""

    code = pasted_code or ""
    error = pasted_error or ""
    filename = processed.filename

    if processed.code:
        code = merge_code_inputs(pasted_code, processed.code)
    elif processed.file_type == "code" and processed.text:
        code = merge_code_inputs(pasted_code, processed.text)
    elif not code.strip() and processed.text:
        code = processed.text[:50_000]

    if processed.error_message:
        error = f"{error}\n{processed.error_message}".strip() if error else processed.error_message

    if processed.transcript and processed.file_type in ("audio", "video"):
        tag = f"[Audio/Video transcript]\n{processed.transcript}"
        error = f"{error}\n\n{tag}".strip() if error else processed.transcript

    return code.strip(), error.strip(), filename
