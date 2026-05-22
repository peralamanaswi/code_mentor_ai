"""Parse analysis reports and extract structured fields for MongoDB storage."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


def detect_error_types(error_msg: str, code: str) -> List[str]:
    """Extract error type keywords from message and code."""
    combined = f"{error_msg}\n{code}".lower()
    known = [
        "nameerror",
        "syntaxerror",
        "indentationerror",
        "typeerror",
        "indexerror",
        "keyerror",
        "attributeerror",
        "zerodivisionerror",
        "importerror",
        "valueerror",
        "runtimeerror",
        "nullpointerexception",
    ]
    return [e for e in known if e in combined]


def extract_fixed_code(report: str) -> str:
    """Pull corrected code block from markdown report."""
    patterns = [
        r"## Corrected Code\s*```[^\n]*\n(.*?)```",
        r"## Corrected Code\s*```\s*\n(.*?)```",
    ]
    for pattern in patterns:
        match = re.search(pattern, report, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_explanation(report: str) -> str:
    """Pull error explanation section."""
    match = re.search(
        r"## Error Explanation\s*(.*?)(?=## |\Z)",
        report,
        re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else report[:1500]


def estimate_confidence_score(error_msg: str, report: str) -> float:
    """Heuristic confidence 0.0–1.0 based on error clarity and report depth."""
    score = 0.5
    if error_msg and len(error_msg) > 10:
        score += 0.15
    if "## Corrected Code" in report:
        score += 0.2
    if len(report) > 500:
        score += 0.1
    if "static analysis" in report.lower() or "unavailable" in report.lower():
        score -= 0.15
    return round(min(1.0, max(0.2, score)), 2)


def parse_bug_report(
    report: str,
    error_msg: str,
    code: str,
) -> Dict[str, str]:
    """Structured bug fields for MongoDB."""
    errors = detect_error_types(error_msg, code)
    detected = error_msg or ", ".join(errors) or "Unknown error"
    return {
        "detected_errors": detected[:5000],
        "explanation": extract_explanation(report),
        "fixed_code": extract_fixed_code(report) or code[:5000],
        "confidence_score": estimate_confidence_score(error_msg, report),
        "error_type": errors[0] if errors else "general",
    }


def parse_complexity_report(report: str, static_report: str) -> Dict[str, str]:
    """Extract complexity metrics from AI/static markdown."""
    cyclomatic = _extract_section(report, "Complexity Level") or static_report[:2000]
    readability = _extract_score_line(report, "Readability Score") or "N/A"
    tips = _extract_section(report, "Optimization Suggestions") or _extract_section(
        report, "Better Coding Practices"
    )
    return {
        "cyclomatic_complexity": cyclomatic[:3000],
        "readability_score": readability,
        "optimization_tips": (tips or report[:3000])[:5000],
    }


def _extract_section(text: str, heading: str) -> str:
    match = re.search(
        rf"## {re.escape(heading)}\s*(.*?)(?=## |\Z)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def _extract_score_line(text: str, heading: str) -> str:
    section = _extract_section(text, heading)
    if section:
        return section.split("\n")[0][:200]
    match = re.search(rf"{heading}[^\n]*", text, re.IGNORECASE)
    return match.group(0)[:200] if match else ""


def build_retrieval_query(code: str, error_msg: str, feature: str) -> str:
    """Build semantic search query from user input."""
    parts = [feature]
    if error_msg:
        parts.append(error_msg[:500])
    if code:
        parts.append(code[:800])
    return "\n".join(parts)
