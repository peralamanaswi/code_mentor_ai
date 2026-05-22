"""Tests for multimodal file router."""

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class FakeUpload:
    """Minimal Streamlit upload stand-in."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def test_route_txt_document() -> None:
    from utils.file_router import route_file

    content = b"def hello():\n    print('hi')\n"
    result = route_file(FakeUpload("test.py", content))
    assert result.success
    assert result.file_type == "code"
    assert "def hello" in result.code


def test_route_plain_txt() -> None:
    from utils.file_router import route_file

    result = route_file(FakeUpload("notes.txt", b"NameError: name 'x' is not defined"))
    assert result.file_type == "document"
    assert result.success


if __name__ == "__main__":
    test_route_txt_document()
    test_route_plain_txt()
    print("File router tests passed.")
