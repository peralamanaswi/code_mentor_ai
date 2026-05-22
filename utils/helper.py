"""UI helpers, theme injection, and shared Streamlit components."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def load_custom_css(theme: str = "dark") -> None:
    """Inject custom CSS for SaaS-like professional UI.

    Args:
        theme: 'dark' or 'light'.
    """
    css_path = ASSETS_DIR / "style.css"
    base_css = ""
    if css_path.exists():
        base_css = css_path.read_text(encoding="utf-8")

    theme_vars = (
        """
        :root {
            --bg-primary: #0f172a;
            --bg-card: #1e293b;
            --text-primary: #f8fafc;
            --accent: #6366f1;
        }
        """
        if theme == "dark"
        else """
        :root {
            --bg-primary: #f8fafc;
            --bg-card: #ffffff;
            --text-primary: #0f172a;
            --accent: #4f46e5;
        }
        """
    )

    st.markdown(
        f"<style>{theme_vars}{base_css}</style>",
        unsafe_allow_html=True,
    )


def render_gradient_header(title: str, subtitle: str = "") -> None:
    """Display gradient heading for pages.

    Args:
        title: Main page title.
        subtitle: Optional subtitle text.
    """
    sub_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="gradient-header">
            <h1>{title}</h1>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_toast(message: str, icon: str = "✅") -> None:
    """Show a brief toast-style notification via Streamlit.

    Args:
        message: User-facing message.
        icon: Emoji prefix.
    """
    st.toast(f"{icon} {message}")


def render_card(title: str, content: str, expanded: bool = True) -> None:
    """Render result inside an expandable card.

    Args:
        title: Card header.
        content: Markdown body.
        expanded: Whether expander starts open.
    """
    with st.expander(title, expanded=expanded):
        st.markdown(content)


def render_loading_spinner(message: str = "Analyzing your code...") -> None:
    """Standard loading message wrapper.

    Args:
        message: Spinner label.
    """
    return st.spinner(message)


def privacy_disclaimer() -> None:
    """Show privacy note in footer areas."""
    st.caption(
        "🔒 Privacy: Uploaded code is not stored permanently. "
        "Reports are generated in your session only."
    )


def detect_language_from_code(code: str, filename: str = "") -> str:
    """Simple heuristic for programming language.

    Args:
        code: Source code.
        filename: Optional filename with extension.

    Returns:
        Language name string.
    """
    fn = (filename or "").lower()
    if fn.endswith(".java") or "public class" in code:
        return "Java"
    if fn.endswith(".cpp") or "#include" in code:
        return "C++"
    if fn.endswith(".js") or "function " in code and "console.log" in code:
        return "JavaScript"
    if fn.endswith(".py") or "def " in code or "import " in code:
        return "Python"
    return "auto"


def format_report_section(title: str, body: str) -> str:
    """Format a report section with consistent markdown.

    Args:
        title: Section heading.
        body: Section content.

    Returns:
        Markdown string.
    """
    return f"### {title}\n\n{body}\n\n---\n"
