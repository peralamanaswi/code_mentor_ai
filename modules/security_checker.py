"""Security analysis using Bandit and AI explanations."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

import streamlit as st

from modules.ai_response import generate_ai_response, is_ai_available
from utils.helper import render_card, show_toast
from utils.multimodal_ui import merge_multimodal_inputs, render_multimodal_uploader
from utils.prompt_templates import security_ai_prompt, static_only_notice
from utils.validators import validate_analysis_input

# Rule-based patterns (Rule + LLM hybrid)
DANGEROUS_PATTERNS: List[Tuple[str, str]] = [
    (r'password\s*=\s*["\']', "Hardcoded Password"),
    (r'api[_-]?key\s*=\s*["\']', "Hardcoded API Key"),
    (r"eval\s*\(", "Unsafe eval()"),
    (r"exec\s*\(", "Unsafe exec()"),
    (r"pickle\.loads", "Unsafe deserialization"),
    (r"os\.system\s*\(", "Command injection risk"),
    (r"subprocess\.call\s*\([^)]*shell\s*=\s*True", "Shell injection risk"),
    (r"SELECT\s+.*\+", "Possible SQL injection (string concat)"),
]


def run_bandit_scan(code: str) -> str:
    """Execute Bandit security linter on Python code.

    Args:
        code: Source code.

    Returns:
        Formatted Bandit findings.
    """
    lines = ["=== Bandit Security Scan ==="]
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            path = tmp.name

        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", path, "-f", "json", "-q"],
            capture_output=True,
            text=True,
            timeout=45,
        )
        Path(path).unlink(missing_ok=True)

        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                results = data.get("results", [])
                if not results:
                    lines.append("No high-confidence issues reported by Bandit.")
                for item in results[:15]:
                    sev = item.get("issue_severity", "?")
                    conf = item.get("issue_confidence", "?")
                    text = item.get("issue_text", "")
                    line = item.get("line_number", "?")
                    lines.append(f"[{sev}/{conf}] Line {line}: {text}")
            except json.JSONDecodeError:
                lines.append(result.stdout[:2000] or "Bandit completed with no JSON output.")
        else:
            lines.append("Bandit: no output (non-Python or clean scan).")
    except Exception as exc:
        lines.append(f"Bandit note: {exc}")

    lines.append("\n=== Rule-Based Pattern Scan ===")
    for pattern, name in DANGEROUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            lines.append(f"⚠️ Detected: {name} (pattern: {pattern})")

    if len(lines) <= 2:
        lines.append("No obvious dangerous patterns in rule scan.")
    return "\n".join(lines)


def analyze_security(code: str) -> Tuple[str, str]:
    """Static Bandit + AI security explanation.

    Args:
        code: Source to scan.

    Returns:
        Tuple of (static_report, display_markdown).
    """
    static = run_bandit_scan(code)
    if is_ai_available():
        prompt = security_ai_prompt(code, static)
        ai = generate_ai_response(prompt)
        if ai:
            return static, ai
    fallback = static_only_notice() + "\n\n" + _fallback_security_markdown(static)
    return static, fallback


def _fallback_security_markdown(static: str) -> str:
    """Beginner-friendly static security report."""
    return f"""## Security Summary
Review the findings below. Never hardcode passwords or API keys.

## Issues Found
See Bandit and pattern scan output.

## Overall Recommendation
- Store secrets in `.env` files
- Use parameterized SQL queries
- Avoid `eval()` on user input
- Validate all file paths before opening

### Scan Details
```
{static}
```
"""


def render_security_page() -> None:
    """Streamlit UI for Secure Code Checker."""
    st.markdown("### 🔐 Secure Code Checker")
    st.markdown(
        "Find security risks like hardcoded secrets, unsafe `eval()`, and injection risks. "
        "Uses **Bandit** and AI explanations."
    )

    code = st.text_area(
        "Paste your code",
        height=220,
        key="security_code",
    )
    _, processed = render_multimodal_uploader("security")

    if st.button("Scan for Security Issues", type="primary", key="sec_btn"):
        merged, _, _ = merge_multimodal_inputs(code, "", processed)
        ok, err = validate_analysis_input(merged)
        if not ok:
            st.warning(err)
            return
        with st.spinner("Running Bandit and security AI..."):
            static, report = analyze_security(merged)
        show_toast("Security scan complete!")
        render_card("🛡️ Security Report", report)
        with st.expander("🔍 Raw Scan Output", expanded=False):
            st.code(static, language="text")
