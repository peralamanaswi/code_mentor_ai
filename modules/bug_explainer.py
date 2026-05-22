"""AI Bug Explainer – interpret errors and suggest fixes."""

from __future__ import annotations

import re
from typing import Optional, Tuple

import streamlit as st

from modules.ai_response import generate_ai_response, is_ai_available
from utils.helper import detect_language_from_code, render_card, show_toast
from utils.multimodal_ui import merge_multimodal_inputs, render_multimodal_uploader
from utils.prompt_templates import bug_explainer_prompt, static_only_notice
from utils.validators import validate_analysis_input, validate_error_message


def static_bug_analysis(code: str, error_msg: str) -> str:
    """Rule-based error hints when AI is unavailable.

    Technique: Rule + LLM hybrid (static rules complement AI).

    Args:
        code: User code.
        error_msg: Error traceback or message.

    Returns:
        Static analysis text.
    """
    hints = []
    combined = f"{error_msg}\n{code}".lower()

    rules = [
        ("nameerror", "A variable or name is used before it is defined."),
        ("syntaxerror", "Python/Java/etc. grammar is broken — check colons, brackets, quotes."),
        ("indentationerror", "Indentation does not match — use consistent spaces (4 spaces in Python)."),
        ("typeerror", "Wrong data type used in an operation."),
        ("indexerror", "List/string index out of range."),
        ("keyerror", "Dictionary key does not exist."),
        ("attributeerror", "Object does not have that method or attribute."),
        ("zerodivisionerror", "Cannot divide by zero."),
        ("importerror", "Module not installed or wrong import path."),
        ("nullpointerexception", "Object is null in Java — initialize before use."),
    ]

    for key, msg in rules:
        if key in combined:
            hints.append(f"- **{key.title()}**: {msg}")

    if "print(name)" in code and "name" not in code.replace("print(name)", ""):
        hints.append('- **Likely issue**: `name` is not defined before `print(name)`.')
        hints.append('- **Fix**: Add `name = "John"` (or your value) before printing.')

    if not hints:
        hints.append("- Review the error line number and check spelling, imports, and brackets.")

    return "\n".join(hints)


def analyze_bug(code: str, error_msg: str, filename: str = "") -> str:
    """Full bug analysis with AI or static fallback.

    Args:
        code: Source code.
        error_msg: Runtime error message.
        filename: Optional upload filename.

    Returns:
        Markdown report for UI.
    """
    lang = detect_language_from_code(code, filename)
    static = static_bug_analysis(code, error_msg)

    if is_ai_available():
        prompt = bug_explainer_prompt(code, error_msg, lang)
        ai = generate_ai_response(prompt)
        if ai:
            return ai

    return _static_bug_report(code, error_msg, static)


def _static_bug_report(code: str, error_msg: str, static: str) -> str:
    """Format static-only bug report."""
    corrected = _suggest_simple_fix(code, error_msg)
    return f"""{static_only_notice()}

## Error Explanation
{error_msg or "Review your code for common mistakes below."}

## Why This Happened
{static}

## Corrected Code
```
{corrected}
```

## Beginner Explanation
Errors are normal when learning. Read the message top-to-bottom; the last line often tells you the problem type.

## Best Practices
- Run code in small steps
- Use meaningful variable names
- Read full error tracebacks

## Optimization Suggestions
- Add comments for tricky lines
- Test one function at a time
"""


def _suggest_simple_fix(code: str, error_msg: str) -> str:
    """Minimal fix suggestion for common NameError demo case."""
    if "name" in (error_msg + code).lower() and "name =" not in code:
        return 'name = "John"\n' + code
    return code + "\n# TODO: Fix based on error message above"


def render_bug_explainer_page() -> None:
    """Streamlit UI for AI Bug Explainer."""
    st.markdown("### 🐛 AI Bug Explainer")
    st.markdown(
        "Paste your code and error message, or upload a **screenshot, PDF, audio, or video**. "
        "Get a beginner-friendly explanation and fixed code."
    )

    code = st.text_area(
        "Your code",
        height=180,
        placeholder="print(name)",
        key="bug_code",
    )
    error_msg = st.text_area(
        "Error message (optional but recommended)",
        height=100,
        placeholder="NameError: name 'name' is not defined",
        key="bug_error",
    )
    _, processed = render_multimodal_uploader("bug")

    if st.button("Explain Bug", type="primary", key="bug_btn"):
        merged, merged_error, fname = merge_multimodal_inputs(code, error_msg, processed)
        ok, err = validate_analysis_input(merged, merged_error)
        if not ok:
            st.warning(err)
            return
        ok_err, err_msg_val = validate_error_message(merged_error)
        if not ok_err:
            st.warning(err_msg_val)
            return

        with st.spinner("AI is analyzing your bug..."):
            report = analyze_bug(merged, merged_error, fname)
        show_toast("Bug analysis ready!")
        render_card("🔧 Bug Analysis Report", report)

        st.download_button(
            "📥 Download Report",
            data=report,
            file_name="bug_report.md",
            mime="text/markdown",
            key="bug_download",
        )
