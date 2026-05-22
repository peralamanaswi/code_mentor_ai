"""Tests for security checker pattern detection."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.security_checker import run_bandit_scan


def test_detects_hardcoded_password_pattern() -> None:
    """Rule scan should flag hardcoded password."""
    code = 'password = "admin123"\nprint(password)'
    report = run_bandit_scan(code)
    assert "Hardcoded Password" in report or "password" in report.lower()


def test_clean_code_scan_runs() -> None:
    """Scan should complete without exception on safe snippet."""
    code = "def add(a, b):\n    return a + b\n"
    report = run_bandit_scan(code)
    assert "Bandit" in report or "Pattern" in report


if __name__ == "__main__":
    test_detects_hardcoded_password_pattern()
    test_clean_code_scan_runs()
    print("All security tests passed.")
