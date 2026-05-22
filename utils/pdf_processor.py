"""PDF text and code extraction."""

from __future__ import annotations

from typing import Any, Dict

from utils.text_extractor import extract_code_from_text, extract_errors_from_text


def process_pdf(file_path: str, filename: str = "document.pdf") -> Dict[str, Any]:
    """Extract text from PDF using PyMuPDF with pdfplumber fallback.
    If the PDF is scanned (contains no text), renders pages to images and runs EasyOCR.

    Args:
        file_path: Path to the temporary PDF file.
        filename: Original filename.

    Returns:
        Dict with text, code, error_message, success.
    """
    import os
    import fitz
    import pdfplumber
    from utils.text_extractor import extract_code_from_text, extract_errors_from_text

    text = ""
    errors: list[str] = []

    # Try PyMuPDF (fitz)
    try:
        doc = fitz.open(file_path)
        pages = []
        for page in doc:
            pages.append(page.get_text())
        text = "\n".join(pages).strip()
        doc.close()
    except Exception as exc:
        errors.append(f"PyMuPDF: {exc}")

    # Fallback: pdfplumber
    if not text.strip():
        try:
            with pdfplumber.open(file_path) as pdf:
                pages = []
                for p in pdf.pages:
                    pages.append(p.extract_text() or "")
                text = "\n".join(pages).strip()
        except Exception as exc:
            errors.append(f"pdfplumber: {exc}")

    # Fallback to OCR for scanned PDFs
    if not text.strip():
        try:
            doc = fitz.open(file_path)
            if len(doc) == 0:
                return {
                    "text": "",
                    "code": "",
                    "error_message": "",
                    "success": False,
                    "error": "The PDF file is empty (contains no pages).",
                }

            from utils.image_processor import _get_ocr_reader, preprocess_image_for_ocr
            import numpy as np
            import tempfile

            reader = _get_ocr_reader()
            ocr_pages = []

            for page_idx, page in enumerate(doc):
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                
                # Write page to temporary image file
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as ptmp:
                    ptmp.write(img_data)
                    ptmp_name = ptmp.name

                try:
                    enhanced_img = preprocess_image_for_ocr(ptmp_name)
                    results = reader.readtext(enhanced_img, detail=0, paragraph=True)
                    page_text = "\n".join(str(r) for r in results if r).strip()
                    if page_text:
                        ocr_pages.append(page_text)
                finally:
                    if os.path.exists(ptmp_name):
                        try:
                            os.unlink(ptmp_name)
                        except OSError:
                            pass

            text = "\n\n".join(ocr_pages).strip()
            doc.close()
        except Exception as exc:
            errors.append(f"Scanned PDF OCR: {exc}")

    if not text.strip():
        err_msg = "Could not extract text from PDF. "
        if errors:
            err_msg += f"Errors encountered: {'; '.join(errors)}"
        else:
            err_msg += "PDF contains no readable text."
        return {
            "text": "",
            "code": "",
            "error_message": "",
            "success": False,
            "error": err_msg,
        }

    code = extract_code_from_text(text)
    err_msg = extract_errors_from_text(text)

    return {
        "text": text,
        "code": code,
        "error_message": err_msg,
        "transcript": "",
        "success": True,
        "error": None,
        "source": "pdf",
        "filename": filename,
    }
