"""Analyze Everything – combined bug, security, complexity report."""

from __future__ import annotations

import streamlit as st

from modules.ai_response import generate_ai_response, is_ai_available
from modules.bug_explainer import analyze_bug, static_bug_analysis
from modules.complexity_analyzer import analyze_complexity, static_complexity_report
from modules.security_checker import analyze_security, run_bandit_scan
from utils.file_handler import save_report_to_disk
from utils.helper import render_card, show_toast
from utils.multimodal_ui import merge_multimodal_inputs, render_multimodal_uploader
from utils.prompt_templates import full_analysis_prompt, static_only_notice
from utils.validators import validate_analysis_input


def build_combined_report(
    code: str,
    error_msg: str,
    filename: str = "",
    source_type: str = "text",
    extra_context: str = "",
) -> str:
    """Run all analyses and produce one professional report.

    Gen AI: Context-aware reasoning (all modules' output in one prompt),
    structured step-by-step report format.

    Args:
        code: Source code.
        error_msg: Optional error message.
        filename: Upload filename.

    Returns:
        Full report markdown.
    """
    bug_static = static_bug_analysis(code, error_msg)
    security_static = run_bandit_scan(code)
    complexity_static = static_complexity_report(code, filename)

    if is_ai_available():
        prompt = full_analysis_prompt(
            code,
            error_msg,
            bug_static,
            security_static,
            complexity_static,
            source_type=source_type,
            extra_context=extra_context,
        )
        ai_report = generate_ai_response(prompt)
        if ai_report:
            return _ensure_report_header(ai_report)

    # Hybrid: stitch module outputs when AI fails or keys missing
    bug_section = analyze_bug(code, error_msg, filename)
    _, sec_md = analyze_security(code)
    _, cx_md = analyze_complexity(code, filename)

    return f"""=========================
CODEMENTOR AI REPORT
=========================

{static_only_notice()}

## 1. Summary Score
Overall: 65/100 (static analysis mode — add API keys for AI scoring)

Brief: Your code was analyzed with automated tools. Review each section below.

## 2. Bug Analysis
{bug_section[:2500]}

## 3. Security Analysis
{sec_md[:2500]}

## 4. Complexity Analysis
{cx_md[:2500]}

## 5. Optimization Suggestions
- Refactor long functions
- Use environment variables for secrets
- Add tests for critical paths
- Improve naming and comments

## 6. Final Recommendation
Keep practicing! Fix security issues first, then readability, then performance.
"""


def _ensure_report_header(report: str) -> str:
    """Ensure combined report has standard header."""
    if "CODEMENTOR AI REPORT" in report.upper():
        return report
    return (
        "=========================\n"
        "CODEMENTOR AI REPORT\n"
        "=========================\n\n" + report
    )


def render_full_analysis_page() -> None:
    """Streamlit UI for Analyze Everything mode."""
    st.markdown("### ⚡ Analyze Everything")
    st.markdown(
        "One click runs **Bug**, **Security**, and **Complexity** analysis "
        "and generates a single professional report."
    )

    code = st.text_area("Paste your code", height=200, key="full_code")
    error_msg = st.text_area(
        "Error message (optional)",
        height=80,
        key="full_error",
    )
    _, processed = render_multimodal_uploader("full")

    if st.button("🚀 Analyze Everything", type="primary", key="full_btn"):
        merged, merged_error, fname = merge_multimodal_inputs(code, error_msg, processed)
        ok, err = validate_analysis_input(merged, merged_error)
        if not ok:
            st.warning(err)
            return

        source_type = processed.file_type if processed else "text"
        extra = ""
        if processed:
            extra = (processed.text or "")[:3000]
            if processed.transcript:
                extra += f"\nTranscript: {processed.transcript[:1500]}"

        with st.spinner("Running multimodal full analysis — please wait…"):
            report = build_combined_report(
                merged, merged_error, fname, source_type, extra
            )

        show_toast("Full report generated!")
        render_card("📋 Combined Report", report)

        save_report_to_disk(report, "full_analysis")
        st.download_button(
            label="📥 Download Full Report",
            data=report,
            file_name="codementor_full_report.md",
            mime="text/markdown",
            key="full_download",
        )
