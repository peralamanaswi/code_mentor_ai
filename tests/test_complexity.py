"""Tests for complexity analyzer heuristics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.complexity_analyzer import static_complexity_report
from utils.validators import validate_code_input, validate_uploaded_file


def test_validate_rejects_empty_code() -> None:
    """Empty code should fail validation."""
    ok, err = validate_code_input("   ")
    assert ok is False
    assert err is not None


def test_validate_rejects_oversized_code() -> None:
    """Code over 50k chars should fail."""
    ok, err = validate_code_input("x" * 50_001)
    assert ok is False


def test_static_complexity_report_python() -> None:
    """Static report should run for simple Python."""
    code = "def f():\n    return 1\n"
    report = static_complexity_report(code, "test.py")
    assert "Radon" in report or "Pylint" in report or "language" in report.lower()


if __name__ == "__main__":
    test_validate_rejects_empty_code()
    test_validate_rejects_oversized_code()
    test_static_complexity_report_python()
    print("All complexity tests passed.")
