"""Image understanding: OCR + error/code detection for screenshots."""

from __future__ import annotations

import io
import re
from typing import Any, Dict, Optional

from utils.text_extractor import extract_code_from_text, extract_errors_from_text

# Lazy-loaded EasyOCR reader (heavy model)
_OCR_READER: Optional[Any] = None


def _get_ocr_reader():
    """Load EasyOCR reader once per process."""
    global _OCR_READER
    if _OCR_READER is None:
        import easyocr

        _OCR_READER = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _OCR_READER


def preprocess_image_for_ocr(file_path: str) -> np.ndarray:
    """Enhance and clean image for OCR processing to handle blurry screenshots."""
    import cv2
    import numpy as np
    from PIL import Image

    # Try reading image using cv2
    img = cv2.imread(file_path, cv2.IMREAD_COLOR)
    if img is None:
        # Fallback to PIL
        with open(file_path, "rb") as f:
            pil_img = Image.open(io.BytesIO(f.read())).convert("RGB")
        img = np.array(pil_img)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Upscale if the image is too small (helpful for screenshots)
    h, w = gray.shape[:2]
    if w < 1200:
        scale = 1200 / w if w > 0 else 2.0
        scale = min(max(scale, 1.5), 3.0)
        new_w = int(w * scale)
        new_h = int(h * scale)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    # Denoise while keeping edges sharp (bilateral filtering)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    # Sharpening kernel
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(gray, -1, kernel)

    return sharpened


def clean_ocr_text(text: str) -> str:
    """Remove trailing/consecutive whitespace while preserving leading spaces."""
    if not text:
        return ""
    lines = []
    for line in text.splitlines():
        stripped = line.rstrip()
        if not stripped:
            continue
        # Reduce multiple spaces between non-whitespace characters to a single space
        cleaned = re.sub(r'(?<=\S) {2,}(?=\S)', ' ', stripped)
        lines.append(cleaned)
    return "\n".join(lines).strip()


def process_image(file_path: str, filename: str = "image.png") -> Dict[str, Any]:
    """Extract text from image via OCR; detect code and errors.

    Args:
        file_path: Path to the temporary image file.
        filename: Original filename.

    Returns:
        Dict with text, code, error_message, success, error.
    """
    ocr_text = ""
    error_note: Optional[str] = None
    import numpy as np

    try:
        # Load reader
        reader = _get_ocr_reader()
        
        # Try OCR on preprocessed image first
        try:
            enhanced_img = preprocess_image_for_ocr(file_path)
            results = reader.readtext(enhanced_img, detail=0, paragraph=True)
            ocr_text = "\n".join(str(r) for r in results if r).strip()
        except Exception as ocr_exc:
            error_note = f"Enhanced OCR failed: {ocr_exc}. Trying fallback..."

        # Fallback to original image if first pass yielded nothing
        if not ocr_text:
            try:
                import cv2
                img_orig = cv2.imread(file_path, cv2.IMREAD_COLOR)
                if img_orig is not None:
                    results = reader.readtext(img_orig, detail=0, paragraph=True)
                    ocr_text = "\n".join(str(r) for r in results if r).strip()
            except Exception as fb_exc:
                error_note = f"OCR failed: {fb_exc}"
                
    except Exception as exc:
        return {
            "text": "",
            "code": "",
            "error_message": "",
            "success": False,
            "error": f"Image processing failed: {exc}",
        }

    ocr_text = clean_ocr_text(ocr_text)

    if not ocr_text:
        ocr_text = "No text detected in image"
        success = False
        error_note = "No text detected in image"
    else:
        success = True

    code = extract_code_from_text(ocr_text)
    errors = extract_errors_from_text(ocr_text)

    if not code and ocr_text and ocr_text != "No text detected in image":
        code = _guess_code_lines(ocr_text)

    return {
        "text": ocr_text,
        "code": code,
        "error_message": errors,
        "transcript": "",
        "success": success,
        "error": error_note if not success else None,
        "source": "image_ocr",
        "filename": filename,
    }


def _fallback_image_hint() -> str:
    """Placeholder when OCR cannot run."""
    return (
        "[Image uploaded — OCR could not run in this environment. "
        "Paste error text manually or deploy with easyocr installed.]"
    )


def _guess_code_lines(text: str) -> str:
    """Heuristic: lines that look like source code."""
    lines = []
    for line in text.splitlines():
        if re.search(r"[{}();=]|def |class |import |#include|print\(", line):
            lines.append(line)
    return "\n".join(lines)
