"""Extract code blocks and error messages from plain text."""

from __future__ import annotations

import re

_CODE_BLOCK_RE = re.compile(r"```[\w]*\n(.*?)```", re.DOTALL)
_ERROR_PATTERNS = [
    re.compile(r"(?i)(name|syntax|type|value|index|key|attribute|indentation)error[:\s].+"),
    re.compile(r"(?i)traceback \(most recent call last\):.+", re.DOTALL),
    re.compile(r"(?i)exception[:\s].+"),
    re.compile(r"(?i)error[:\s].+"),
    re.compile(r"(?i)compilation failed.+"),
]


def extract_code_from_text(text: str) -> str:
    """Pull fenced code blocks or code-like lines from text."""
    if not text:
        return ""
    blocks = _CODE_BLOCK_RE.findall(text)
    if blocks:
        return "\n\n".join(b.strip() for b in blocks)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(
            stripped.startswith(k)
            for k in (
                "def ", "class ", "import ", "from ", "public ", "#include",
                "function ", "console.", "print(", "if ", "for ", "while ",
            )
        ):
            lines.append(line)
    return "\n".join(lines) if lines else ""


def extract_errors_from_text(text: str) -> str:
    """Detect error messages in OCR or document text."""
    if not text:
        return ""
    found = []
    for pat in _ERROR_PATTERNS:
        for m in pat.finditer(text):
            snippet = m.group(0).strip()
            if snippet and snippet not in found:
                found.append(snippet[:500])
    return "\n".join(found[:3])
