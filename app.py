"""
CodeMentor AI – Smart AI Coding Assistant for Beginners
Main Streamlit application entry point.
"""

from __future__ import annotations

import sys
from pathlib import Path
import os

# Ensure project root is on path for imports
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv

from modules.ai_response import is_ai_available
from modules.bug_explainer import render_bug_explainer_page
from modules.complexity_analyzer import render_complexity_page
from modules.full_analysis import render_full_analysis_page
from modules.interview_assistant import render_interview_page
from modules.history_page import render_history_page
from modules.security_checker import render_security_page
from modules.mentor_engine import backend_status
from utils.helper import load_custom_css, privacy_disclaimer, render_gradient_header

load_dotenv()

# Page config must be first Streamlit command
st.set_page_config(
    page_title="CodeMentor AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "Home": "home",
    "Bug Explainer": "bug",
    "Interview Assistant": "interview",
    "Complexity Analyzer": "complexity",
    "Security Checker": "security",
    "Analyze Everything": "full",
    "History & Memory": "history",
    "About Project": "about",
}

# Home page cards → sidebar radio label
HOME_FEATURES = [
    ("🐛", "Bug Explainer", "bug", "Understand errors and get fixed code"),
    ("💼", "Interview Assistant", "interview", "Practice questions with scores"),
    ("📊", "Complexity Analyzer", "complexity", "Radon + Pylint insights"),
    ("🔐", "Security Checker", "security", "Bandit-powered safety scan"),
    ("⚡", "Analyze Everything", "full", "One combined professional report"),
    ("📜", "History & Memory", "history", "MongoDB sessions & similar bugs"),
    ("🎓", "About Project", "about", "Learn how CodeMentor AI works"),
    ("📎", "Multimodal AI", "about", "Images, PDF, audio & video support"),
]

PAGE_KEY_TO_LABEL = {key: label for label, key in PAGES.items()}


def init_session_state() -> None:
    """Initialize theme and navigation state."""
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"


def render_sidebar() -> str:
    """Render sidebar navigation and return selected page key.

    Returns:
        Page key string.
    """
    with st.sidebar:
        logo_path = ROOT / "assets" / "logo.png"
        if logo_path.exists():
            st.image(str(logo_path), width=120)
        st.markdown('<p class="sidebar-brand">CodeMentor AI</p>', unsafe_allow_html=True)
        st.caption("Smart coding assistant for beginners")

        st.divider()

        # Dark / Light theme toggle
        theme_label = "🌙 Dark Mode" if st.session_state.theme == "light" else "☀️ Light Mode"
        if st.button(theme_label, use_container_width=True, key="theme_toggle"):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()

        st.divider()

        # Keep radio in sync with current page so History is reachable from any screen
        page_labels = list(PAGES.keys())
        page_values = list(PAGES.values())
        current = st.session_state.get("current_page", "home")
        try:
            radio_index = page_values.index(current)
        except ValueError:
            radio_index = 0

        selection = st.radio(
            "Navigate",
            page_labels,
            index=radio_index,
            key="nav_radio",
        )
        page_key = PAGES[selection]

        st.divider()
        bs = backend_status()
        if bs["mongodb"]:
            st.caption("🟢 MongoDB connected")
        else:
            st.caption("⚪ MongoDB — set MONGODB_URI in .env")
        if bs["chromadb"]:
            st.caption("🟢 ChromaDB memory active")
        else:
            st.caption("⚪ ChromaDB — install chromadb + sentence-transformers")

        st.divider()

    return page_key


def navigate_to_page(page_key: str) -> None:
    """Switch sidebar navigation and open the selected module.

    Args:
        page_key: Internal page id (e.g. 'bug', 'interview').
    """
    label = PAGE_KEY_TO_LABEL.get(page_key, "Home")
    # Update the sidebar radio selection only if it exists
    if "nav_radio" in st.session_state:
        try:
            st.session_state["nav_radio"] = label
        except Exception:
            # Fallback: ignore if widget state cannot be set
            pass
    # Always update current page and trigger a rerun
    st.session_state.current_page = page_key
    st.rerun()


def render_home() -> None:
    """Professional landing page with clickable module cards."""
    render_gradient_header(
        "CodeMentor AI",
        "Your friendly AI coding mentor — learn, debug, and grow with confidence.",
    )

    st.markdown(
        """
        <div class="hero-card">
        <p>Built for <strong>college students</strong> and beginner programmers.
        Paste code or upload <strong>images, PDFs, audio, video, and code files</strong> —
        get clear explanations in simple English.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Choose a tool")
    st.caption("Click any card below to open that module (or use the sidebar).")

    c1, c2, c3 = st.columns(3)
    for i, (icon, title, page_key, desc) in enumerate(HOME_FEATURES):
        col = [c1, c2, c3][i % 3]
        with col:
            st.markdown(
                f'<div class="feature-card-preview">'
                f'<div class="feature-icon">{icon}</div>'
                f"<strong>{title}</strong></div>",
                unsafe_allow_html=True,
            )
            if st.button(
                f"Open {title}",
                key=f"home_nav_{page_key}_{i}",
                use_container_width=True,
                type="primary",
            ):
                navigate_to_page(page_key)
            st.caption(desc)

    st.divider()
    st.subheader("Quick Start")
    st.code(
        "git clone <your-repo>\n"
        "pip install -r requirements.txt\n"
        "copy .env.example .env   # add API keys\n"
        "python -m streamlit run app.py",
        language="bash",
    )

    with st.expander("Example: NameError fix"):
        st.code('print(name)\n\n# Error: NameError', language="python")
        st.markdown(
            "**Fix:** Define the variable first: `name = \"John\"` then `print(name)`"
        )


def render_about() -> None:
    """About page with Gen AI techniques and diagrams."""
    render_gradient_header("About CodeMentor AI", "Project overview for students & viva")

    st.markdown("## What is CodeMentor AI?")
    st.markdown(
        "A **Generative AI** web app that helps beginners understand bugs, "
        "practice interviews, analyze complexity, and write secure code."
    )

    st.markdown("## Gen AI Techniques Used")
    techniques = [
        ("Prompt Engineering", "Structured prompts in `utils/prompt_templates.py`"),
        ("Context-Aware Reasoning", "Code + error + language sent together to LLM"),
        ("Natural Language Generation", "Groq/Gemini produce beginner-friendly text"),
        ("Error Interpretation", "Bug Explainer module"),
        ("AI-based Recommendations", "Interview feedback & optimization tips"),
        ("Rule + LLM Hybrid", "Bandit/Radon/Pylint + AI explanations"),
        ("Structured Step-by-Step Reasoning", "Analyze Everything report sections"),
        ("Multimodal AI", "OCR, PDF, Whisper, video frames via `utils/file_router.py`"),
    ]
    for name, where in techniques:
        st.markdown(f"- **{name}**: {where}")

    st.markdown("## Architecture Diagram")
    st.markdown(
        """
```mermaid
flowchart TB
    User[User Browser] --> UI[Streamlit app.py]
    UI --> M1[Bug Explainer]
    UI --> M2[Interview Assistant]
    UI --> M3[Complexity Analyzer]
    UI --> M4[Security Checker]
    UI --> M5[Full Analysis]
    M1 --> AI[ai_response.py]
    M2 --> AI
    M3 --> Static[Radon / Pylint]
    M3 --> AI
    M4 --> Bandit[Bandit]
    M4 --> AI
    M5 --> M1
    M5 --> M3
    M5 --> M4
    AI --> Groq[Groq API]
    Groq -->|fail retry| Gemini[Gemini API]
    Groq -->|fail| StaticOnly[Static Only Mode]
```
        """
    )

    st.markdown("## Workflow")
    st.markdown(
        """
1. User opens app → selects module from sidebar  
2. Pastes code or uploads multimodal files (images, PDF, audio, video, code)  
3. Validators check size and file type  
4. Module runs static tools and/or AI  
5. Results shown in expandable cards  
6. User downloads report (Analyze Everything)  
        """
    )

    st.markdown("## Privacy")
    st.info("Uploaded code is **not stored permanently**. Reports are session-based.")

    with st.expander("Viva Questions & Answers"):
        st.markdown(
            """
**Q1: Why Groq as primary API?**  
A: Fast inference and free tier suitable for student projects.

**Q2: What is fallback logic?**  
A: Groq with 2 retries → Gemini → static-only analysis.

**Q3: What is cyclomatic complexity?**  
A: Metric counting independent paths in code; higher = harder to test.

**Q4: What does Bandit do?**  
A: Finds common security issues in Python source code.

**Q5: What is hybrid AI + rules?**  
A: Tools give facts; LLM explains them in simple language for beginners.
            """
        )

    st.markdown("## Multimodal Support")
    st.markdown(
        """
- **Images** — OCR error screenshots (EasyOCR + OpenCV)  
- **PDF** — Assignments & docs (PyMuPDF / pdfplumber)  
- **DOCX/TXT** — Interview answers (python-docx)  
- **Audio** — Coding doubts via Whisper  
- **Video** — Lectures & screen recordings (moviepy + frame OCR)  
- **Smart routing** — `utils/file_router.py` auto-detects file type  
        """
    )

    with st.expander("Future Enhancements"):
        st.markdown(
            """
- Multi-file project analysis  
- GitHub repo URL import  
- Hindi/regional language support  
- Classroom teacher dashboard  
            """
        )

    with st.expander("Presentation Brief (2 min)"):
        st.markdown(
            """
CodeMentor AI is a Streamlit app for beginner programmers. It uses Groq and Gemini 
to explain bugs, score interview answers, and combine security and complexity scans 
into one report. Static tools (Radon, Pylint, Bandit) ensure value even without API keys. 
Modular Python design makes it easy for students to learn and extend.
            """
        )


def main() -> None:
    """Application entry point."""
    init_session_state()
    load_custom_css(st.session_state.theme)

    # Sidebar on every page — otherwise History and other modules are unreachable
    page_key = render_sidebar()
    st.session_state.current_page = page_key

    # Render the appropriate page
    if page_key == "home":
        render_home()
    elif page_key == "bug":
        render_gradient_header("AI Bug Explainer", "Learn why errors happen and how to fix them")
        render_bug_explainer_page()
    elif page_key == "interview":
        render_gradient_header("Interview Assistant", "Practice and improve your answers")
        render_interview_page()
    elif page_key == "complexity":
        render_gradient_header("Complexity Analyzer", "Measure readability and maintainability")
        render_complexity_page()
    elif page_key == "security":
        render_gradient_header("Secure Code Checker", "Find vulnerabilities early")
        render_security_page()
    elif page_key == "full":
        render_gradient_header("Analyze Everything", "Complete code health report")
        render_full_analysis_page()
    elif page_key == "history":
        render_gradient_header("History & Memory", "Past sessions and semantic bug search")
        render_history_page()
    elif page_key == "about":
        render_about()

    bs = backend_status()
    if bs["mongodb"]:
        footer = "🔒 Code is stored only when MongoDB is configured — used for history & learning memory."
    else:
        footer = "🔒 Uploaded code is not stored permanently (enable MONGODB_URI for optional history)."
    st.markdown(f'<p class="privacy-footer">{footer}</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
