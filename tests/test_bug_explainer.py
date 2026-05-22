"""Tests for bug explainer static analysis."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.bug_explainer import analyze_bug, static_bug_analysis


def test_static_detects_nameerror_hint() -> None:
    """Static analysis should hint NameError for undefined name."""
    code = "print(name)"
    error = "NameError: name 'name' is not defined"
    result = static_bug_analysis(code, error)
    assert "name" in result.lower() or "defined" in result.lower()


def test_analyze_bug_returns_markdown_without_api() -> None:
    """Fallback report should contain key sections."""
    report = analyze_bug("print(x)", "NameError", "")
    assert "Error Explanation" in report or "error" in report.lower()
    assert "Corrected Code" in report or "```" in report


if __name__ == "__main__":
    test_static_detects_nameerror_hint()
    test_analyze_bug_returns_markdown_without_api()
    print("All bug explainer tests passed.")
