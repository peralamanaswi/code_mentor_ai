"""Streamlit History page — MongoDB sessions + ChromaDB similar bug search."""

from __future__ import annotations

import streamlit as st

from modules.chromadb_manager import (
    is_chromadb_available,
    query_similar,
    retrieve_similar_bugs,
)
from modules.mentor_engine import backend_status
from modules.mongodb import (
    fetch_all_history_summary,
    fetch_bug_results,
    fetch_code_history,
    fetch_complexity_results,
    fetch_mentor_history,
    fetch_user_queries,
    is_mongodb_available,
    search_bug_results,
    search_mentor_history,
)


def render_history_page() -> None:
    """Display stored sessions and semantic recommendations."""
    st.markdown("### 📜 Session History & Coding Memory")
    st.caption(
        "View past analyses stored in **MongoDB** and find **similar bugs** "
        "via **ChromaDB** semantic search."
    )

    try:
        import pymongo  # noqa: F401
    except ImportError:
        st.error(
            "Missing **pymongo**. Run: `pip install pymongo chromadb sentence-transformers` "
            "then restart Streamlit."
        )

    status = backend_status()
    c1, c2 = st.columns(2)
    with c1:
        if status["mongodb"]:
            st.success("MongoDB connected")
        else:
            st.warning("MongoDB offline — set `MONGODB_URI` in `.env`")
    with c2:
        if status["chromadb"]:
            st.success("ChromaDB memory active")
        else:
            st.warning("ChromaDB offline — install chromadb & sentence-transformers")

    if not status["mongodb"] and not status["chromadb"]:
        st.info(
            "Backends are offline. You can still use the tabs below — "
            "configure **MONGODB_URI** in `.env` and install "
            "`chromadb` + `sentence-transformers`, then run analyses from other tools."
        )

    if status["mongodb"]:
        summary = fetch_all_history_summary()
        st.markdown("#### Storage overview")
        cols = st.columns(6)
        labels = [
            ("Queries", "user_queries"),
            ("Code", "code_history"),
            ("Bugs", "bug_results"),
            ("Complexity", "complexity_results"),
            ("Mentor", "mentor_history"),
            ("Interviews", "interviews"),
        ]
        for col, (label, key) in zip(cols, labels):
            col.metric(label, summary.get(key, 0))

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "Debugging",
            "Code uploads",
            "Complexity",
            "Mentor Q&A",
            "Queries",
            "Similar bugs",
        ]
    )

    with tab1:
        _render_bug_history()

    with tab2:
        _render_code_history()

    with tab3:
        _render_complexity_history()

    with tab4:
        _render_mentor_history()

    with tab5:
        _render_query_history()

    with tab6:
        _render_similar_bugs()


def _render_bug_history() -> None:
    """Previous debugging sessions from MongoDB."""
    st.markdown("#### Previous debugging sessions")
    keyword = st.text_input("Search bugs", key="hist_bug_search", placeholder="NameError, syntax...")
    if keyword:
        records = search_bug_results(keyword)
    else:
        records = fetch_bug_results(limit=30)

    if not records:
        st.info("No bug sessions stored yet. Use **Bug Explainer** to create one.")
        return

    for rec in records:
        with st.expander(
            f"🐛 {rec.get('detected_errors', 'Error')[:60]} — {rec.get('timestamp', '')}",
            expanded=False,
        ):
            st.markdown(f"**Language:** {rec.get('language', 'auto')}")
            st.markdown(f"**Confidence:** {rec.get('confidence_score', 'N/A')}")
            st.markdown(f"**Explanation:**\n{rec.get('explanation', '')[:1500]}")
            if rec.get("fixed_code"):
                st.code(rec["fixed_code"][:2000], language="python")


def _render_code_history() -> None:
    """Uploaded code history."""
    st.markdown("#### Uploaded code history")
    records = fetch_code_history(limit=25)
    if not records:
        st.info("No code uploads stored yet.")
        return
    for rec in records:
        with st.expander(f"📄 {rec.get('filename', 'code')} — {rec.get('upload_time', '')}"):
            st.markdown(f"**Language:** {rec.get('language', 'auto')}")
            st.code(rec.get("code_content", "")[:2500], language=rec.get("language", "python"))


def _render_complexity_history() -> None:
    """Complexity analysis history."""
    st.markdown("#### Complexity analysis history")
    records = fetch_complexity_results(limit=25)
    if not records:
        st.info("No complexity sessions yet. Use **Complexity Analyzer**.")
        return
    for rec in records:
        with st.expander(f"📊 {rec.get('readability_score', 'Score')} — {rec.get('timestamp', '')}"):
            st.markdown(f"**Cyclomatic / level:** {rec.get('cyclomatic_complexity', '')[:500]}")
            st.markdown(f"**Tips:**\n{rec.get('optimization_tips', '')[:1200]}")


def _render_mentor_history() -> None:
    """Stored AI mentor responses."""
    st.markdown("#### Stored mentor responses")
    keyword = st.text_input("Search mentor", key="hist_mentor_search")
    if keyword:
        records = search_mentor_history(keyword)
    else:
        records = fetch_mentor_history(limit=25)

    if not records:
        st.info("No mentor history yet.")
        return
    for rec in records:
        with st.expander(f"💬 {rec.get('module', 'mentor')} — {rec.get('timestamp', '')}"):
            st.markdown(f"**Question:** {rec.get('user_question', '')[:500]}")
            st.markdown(f"**Response:**\n{rec.get('ai_response', '')[:2000]}")


def _render_query_history() -> None:
    """User query log."""
    st.markdown("#### User queries")
    records = fetch_user_queries(limit=30)
    if not records:
        st.info("No queries logged yet.")
        return
    for rec in records:
        st.markdown(
            f"- **{rec.get('timestamp', '')}** [{rec.get('module', '')}] "
            f"({rec.get('programming_language', '')}): {rec.get('user_query', '')[:200]}"
        )


def _render_similar_bugs() -> None:
    """ChromaDB semantic search for similar past bugs."""
    st.markdown("#### Similar bug recommendations")
    if not is_chromadb_available():
        st.warning("ChromaDB not available. Install dependencies and run a bug analysis first.")
        return

    query = st.text_area(
        "Describe your error or paste traceback",
        height=100,
        placeholder="NameError: name 'x' is not defined",
        key="similar_bug_query",
    )
    language = st.selectbox(
        "Filter by language (optional)",
        ["Any", "python", "java", "javascript", "cpp", "auto"],
        key="similar_bug_lang",
    )

    if st.button("Find similar bugs", type="primary", key="similar_bug_btn"):
        if not query.strip():
            st.warning("Enter an error description.")
            return
        lang = None if language == "Any" else language
        with st.spinner("Searching coding memory..."):
            hits = retrieve_similar_bugs(query, language=lang or "auto", n=5)
            if not hits:
                hits = query_similar(query, n_results=5, topic="bug")

        if not hits:
            st.info("No similar sessions found yet. Analyze a few bugs first to build memory.")
            return

        st.success(f"Found {len(hits)} similar session(s)")
        for i, hit in enumerate(hits, 1):
            meta = hit.get("metadata", {})
            sim = hit.get("similarity", "N/A")
            with st.expander(f"Match {i} — similarity {sim} — {meta.get('error_type', '')}"):
                st.caption(
                    f"Topic: {meta.get('topic')} | Lang: {meta.get('language')} | "
                    f"File: {meta.get('filename')} | Time: {meta.get('timestamp', '')}"
                )
                st.markdown(hit.get("document", ""))
