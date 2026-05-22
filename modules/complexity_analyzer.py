"""Code complexity analysis using Radon, Pylint, and AI suggestions."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import streamlit as st

from modules.ai_response import generate_ai_response, is_ai_available
from utils.helper import detect_language_from_code, render_card, show_toast
from utils.multimodal_ui import merge_multimodal_inputs, render_multimodal_uploader
from utils.prompt_templates import complexity_ai_prompt, static_only_notice
from utils.validators import validate_analysis_input


def run_radon_analysis(code: str) -> str:
    """Run Radon cyclomatic complexity on Python code.

    Args:
        code: Source code (Python recommended).

    Returns:
        Human-readable report string.
    """
    lines: list[str] = []
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        result = subprocess.run(
            [sys.executable, "-m", "radon", "cc", tmp_path, "-a", "-j"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            for _filepath, blocks in data.items():
                for block in blocks:
                    rank = block.get("rank", "?")
                    name = block.get("name", "unknown")
                    complexity = block.get("complexity", 0)
                    lines.append(f"- {name}: complexity {complexity} (rank {rank})")
            mi_result = subprocess.run(
                [sys.executable, "-m", "radon", "mi", tmp_path, "-s"],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if mi_result.stdout.strip():
                lines.append(f"Maintainability index: {mi_result.stdout.strip()}")
        else:
            lines.append("Radon: No Python blocks found or analysis skipped.")
    except FileNotFoundError:
        lines.append("Radon not installed.")
    except Exception as exc:
        lines.append(f"Radon analysis note: {exc}")
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except NameError:
            pass

    if not lines:
        return "Radon: Provide Python (.py) code for cyclomatic complexity metrics."
    return "\n".join(lines)


def run_pylint_analysis(code: str) -> str:
    """Run Pylint on Python code snippet.

    Args:
        code: Python source.

    Returns:
        Summary of pylint messages.
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            path = tmp.name

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pylint",
                path,
                "--disable=C0114,C0115,C0116",
                "--score=y",
                "--output-format=text",
            ],
            capture_output=True,
            text=True,
            timeout=45,
        )
        Path(path).unlink(missing_ok=True)
        output = (result.stdout or "") + (result.stderr or "")
        if "rated at" in output.lower() or result.stdout:
            # Extract last 40 lines max
            tail = "\n".join(output.strip().splitlines()[-25:])
            return f"Pylint summary:\n{tail}"
        return "Pylint: Limited issues or non-Python code."
    except Exception as exc:
        return f"Pylint note: {exc}"


def static_complexity_report(code: str, filename: str = "") -> str:
    """Combine static tool outputs.

    Args:
        code: Source code.
        filename: Optional filename.

    Returns:
        Combined static report.
    """
    lang = detect_language_from_code(code, filename)
    parts = [f"Detected language hint: {lang}", "", "=== Radon (Cyclomatic Complexity) ==="]
    if lang in ("Python", "auto") or filename.endswith(".py"):
        parts.append(run_radon_analysis(code))
    else:
        parts.append("Radon applies to Python. Showing general metrics only.")
        parts.append(_generic_complexity_heuristics(code))

    parts.extend(["", "=== Pylint (Readability / Style) ==="])
    if lang in ("Python", "auto") or filename.endswith(".py"):
        parts.append(run_pylint_analysis(code))
    else:
        parts.append("Pylint applies to Python. Use heuristic analysis.")
        parts.append(_generic_complexity_heuristics(code))

    return "\n".join(parts)


def _generic_complexity_heuristics(code: str) -> str:
    """Simple line-based heuristics for non-Python code.

    Args:
        code: Any source code.

    Returns:
        Heuristic report.
    """
    lines = code.splitlines()
    func_count = sum(
        1
        for ln in lines
        if any(k in ln for k in ("def ", "function ", "void ", "int main", "class "))
    )
    loop_nested = code.count("for ") + code.count("while ")
    return (
        f"Lines: {len(lines)}\n"
        f"Functions/classes hints: {func_count}\n"
        f"Loop constructs: {loop_nested}\n"
        f"Max nesting estimate: {'High' if loop_nested > 5 else 'Medium' if loop_nested > 2 else 'Low'}"
    )


def analyze_complexity(code: str, filename: str = "") -> Tuple[str, str]:
    """Run static + AI complexity analysis.

    Args:
        code: Source code.
        filename: Original filename if any.

    Returns:
        Tuple of (static_report, full_display_markdown).
    """
    static = static_complexity_report(code, filename)
    ai_part = ""
    if is_ai_available():
        prompt = complexity_ai_prompt(code, static)
        ai_part = generate_ai_response(prompt) or ""
    if not ai_part:
        ai_part = static_only_notice() + "\n\n" + _fallback_complexity_markdown(static)
    return static, ai_part


def _fallback_complexity_markdown(static: str) -> str:
    """Format static-only complexity for display."""
    return f"""## Complexity Level
See static analysis below.

## Readability Score
Run Pylint on Python for a score.

## Maintainability
Review function length and naming.

## Optimization Suggestions
- Break large functions into smaller ones
- Improve variable naming
- Reduce nested loops

## Better Coding Practices
- Add comments for tricky logic
- Follow language style guides
- Write small testable functions

### Static Analysis Details
```
{static}
```
"""


def render_complexity_page() -> None:
    """Streamlit UI for Code Complexity Analyzer."""
    st.markdown("### 📊 Code Complexity Analyzer")
    st.markdown(
        "Understand how complex your code is and how to make it easier to read and maintain. "
        "Uses **Radon**, **Pylint**, and AI recommendations."
    )

    code = st.text_area(
        "Paste your code",
        height=220,
        placeholder="def hello():\n    print('Hi')",
        key="complexity_code",
    )
    _, processed = render_multimodal_uploader("complexity")

    if st.button("Analyze Complexity", type="primary", key="cx_analyze"):
        merged, _, fname = merge_multimodal_inputs(code, "", processed)
        ok, err = validate_analysis_input(merged)
        if not ok:
            st.warning(err)
            return
        with st.spinner("Running Radon, Pylint, and AI analysis..."):
            static, report = analyze_complexity(merged, fname)
        show_toast("Complexity analysis complete!")
        render_card("📈 Analysis Results", report)
        with st.expander("🔧 Static Tool Output", expanded=False):
            st.code(static, language="text")
