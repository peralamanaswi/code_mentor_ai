"""AI Coding Interview Assistant – text and voice interview modes."""

from __future__ import annotations

import re
import time
from typing import Optional

import streamlit as st

from modules.ai_response import generate_ai_response, is_ai_available
from utils.helper import render_card, show_toast
from utils.interview_question_bank import get_category_label, get_questions_for_category
from utils.multimodal_ui import merge_multimodal_inputs, render_multimodal_uploader
from utils.prompt_templates import (
    interview_evaluate_prompt,
    interview_question_prompt,
    voice_interview_evaluate_prompt,
)

LANGUAGES = ["Python", "Java", "C++", "JavaScript"]
DIFFICULTIES = ["Beginner", "Intermediate", "Advanced"]
INTERVIEW_MODES = ["Text", "Voice"]


def generate_question(language: str, difficulty: str) -> str:
    """Generate interview question using AI only.

    Raises:
        RuntimeError: If AI is unavailable or no response is returned.
    """
    if not is_ai_available():
        raise RuntimeError("AI unavailable – provide your own API key in the sidebar.")
    prompt = interview_question_prompt(language, difficulty)
    result = generate_ai_response(prompt)
    if result:
        return result.strip()
    raise RuntimeError("AI did not return a response.")


def _fallback_question(language: str, difficulty: str) -> str:
    """Static question bank when AI unavailable."""
    bank = {
        ("Python", "Beginner"): "What is a variable in Python? Give an example.",
        ("Python", "Intermediate"): "Explain the difference between a list and a tuple.",
        ("Python", "Advanced"): "How does the GIL affect multi-threading in Python?",
        ("Java", "Beginner"): "What is the difference between `==` and `.equals()` in Java?",
        ("JavaScript", "Beginner"): "What is the difference between `let`, `const`, and `var`?",
        ("C++", "Beginner"): "What is a pointer and why is it used?",
    }
    return bank.get(
        (language, difficulty),
        f"Explain a core concept in {language} at {difficulty} level.",
    )


def evaluate_answer(
    language: str,
    difficulty: str,
    question: str,
    answer: str,
    voice_mode: bool = False,
) -> str:
    """Evaluate candidate answer with AI or rubric fallback."""
    if not (answer or "").strip():
        return "Please provide an answer before submitting for evaluation."

    if is_ai_available():
        if voice_mode:
            prompt = voice_interview_evaluate_prompt(
                language, difficulty, question, answer
            )
        else:
            prompt = interview_evaluate_prompt(language, difficulty, question, answer)
        result = generate_ai_response(prompt)
        if result:
            return result

    return _fallback_evaluation(answer, voice_mode=voice_mode)


def _fallback_evaluation(answer: str, voice_mode: bool = False) -> str:
    """Simple heuristic scoring without AI."""
    words = len(answer.split())
    score = min(10, max(4, words // 10 + 5))
    extra = ""
    if voice_mode:
        extra = """
## Missing Concepts
- Expand with more technical terms from the question

## Confidence Analysis
Medium — based on answer length

## Communication Suggestions
- Speak in complete sentences
- Pause briefly, then explain one example
"""
    return f"""## Score
{score}/10

## Feedback
Good effort! Expand your answer with examples and definitions.

## Mistakes
- Answer may be too short or missing key terms

## Suggested Improvements
- Add a real-world example
- Define technical terms in simple words

## Better Answer
Provide a clear definition, one example, and when to use the concept in real projects.
{extra}
"""


def parse_score(report: str) -> Optional[str]:
    """Extract score like '7/10' or '6.5/10' from report."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", report)
    return match.group(0) if match else None


def _category_key(language: str, difficulty: str) -> str:
    return f"{language}|{difficulty}"


def _sync_questions_for_category(language: str, difficulty: str) -> list[str]:
    """Load question set when language or difficulty changes."""
    key = _category_key(language, difficulty)
    if st.session_state.get("interview_category_key") != key:
        questions = get_questions_for_category(language, difficulty)
        st.session_state.interview_questions = questions
        st.session_state.interview_category_key = key
        st.session_state.interview_question_index = 0
        st.session_state.interview_question = questions[0] if questions else ""
    return st.session_state.get("interview_questions", [])


def _render_question_set(language: str, difficulty: str) -> None:
    """Show 7–10 numbered questions for the selected category."""
    questions = _sync_questions_for_category(language, difficulty)
    if not questions:
        st.warning("No questions available for this category.")
        return

    label = get_category_label(language, difficulty)
    st.markdown(f"#### 📚 {label} — {len(questions)} practice questions")

    for idx, question in enumerate(questions, start=1):
        st.markdown(f"**{idx}.** {question}")

    options = list(range(len(questions)))
    selected = st.radio(
        "Select a question to practice",
        options=options,
        format_func=lambda i: f"Question {i + 1}",
        key=f"int_question_select_{_category_key(language, difficulty)}",
        horizontal=True,
    )
    st.session_state.interview_question_index = selected
    st.session_state.interview_question = questions[selected]

    st.info(f"**Active question:** {st.session_state.interview_question}")


def _render_text_interview(language: str, difficulty: str) -> None:
    """Original text-based interview flow (unchanged)."""
    answer = st.text_area(
        "Your answer",
        height=150,
        placeholder="Type your answer here...",
        key="int_answer",
    )
    st.caption("Or upload DOCX/TXT/PDF/audio with your written or spoken answer.")
    _, processed = render_multimodal_uploader("interview")

    if st.button("✅ Evaluate Answer", key="eval_btn"):
        if not st.session_state.get("interview_question"):
            st.warning("Select a practice question above first!")
            return
        merged_answer, _, _ = merge_multimodal_inputs(answer, "", processed)
        if not merged_answer.strip():
            st.warning("Please type or upload your answer.")
            return
        with st.spinner("Evaluating your answer..."):
            report = evaluate_answer(
                language,
                difficulty,
                st.session_state.interview_question,
                merged_answer,
                voice_mode=False,
            )
        score = parse_score(report)
        if score:
            st.metric("Your Score", score)
            from utils.mongo_client import save_interview_record

            record = {
                "language": language,
                "difficulty": difficulty,
                "question": st.session_state.interview_question,
                "answer": merged_answer,
                "score": score,
                "timestamp": time.time(),
            }
            try:
                save_interview_record(record)
            except Exception as e:
                st.warning(f"⚠️ Failed to store interview data: {e}")
        show_toast("Evaluation complete!")
        render_card("📝 Interview Feedback", report)


def render_interview_page() -> None:
    """Streamlit UI – Text Interview Mode + Voice Interview Mode."""
    st.markdown("### 💼 AI Coding Interview Assistant")
    st.markdown(
        "Each **language + difficulty** category includes **8 practice questions** (7–10 range). "
        "Pick one, answer in **text** or **voice** mode, then evaluate."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        language = st.selectbox("Select Language", LANGUAGES, key="int_lang")
    with col2:
        difficulty = st.selectbox("Difficulty", DIFFICULTIES, key="int_diff")
    with col3:
        interview_mode = st.selectbox(
            "Choose Interview Mode",
            INTERVIEW_MODES,
            key="int_mode",
            help="Text: type your answer. Voice: speak using your microphone.",
        )

    enable_voice = False
    if interview_mode == "Voice":
        enable_voice = st.toggle(
            "🔊 Enable Voice",
            value=True,
            key="int_enable_voice",
            help="AI reads the interview question aloud using text-to-speech.",
        )

    if "interview_question" not in st.session_state:
        st.session_state.interview_question = ""
    if "interview_questions" not in st.session_state:
        st.session_state.interview_questions = []
    if "interview_category_key" not in st.session_state:
        st.session_state.interview_category_key = ""

    _render_question_set(language, difficulty)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🎲 Extra AI Question", key="gen_q"):
            if not is_ai_available():
                st.warning("AI unavailable — use the practice questions above.")
            else:
                with st.spinner("Generating bonus question..."):
                    try:
                        st.session_state.interview_question = generate_question(
                            language, difficulty
                        )
                        _clear_voice_state_on_new_question()
                        show_toast("Bonus AI question loaded!")
                    except RuntimeError as exc:
                        st.error(str(exc))
    with col_b:
        if interview_mode == "Voice" and enable_voice and st.session_state.interview_question:
            if st.button("🔊 Read active question aloud", key="read_q"):
                from modules.voice_interview import speak_question_if_enabled

                speak_question_if_enabled(st.session_state.interview_question, True)

    if (
        interview_mode == "Voice"
        and enable_voice
        and st.session_state.get("voice_tts_bytes")
    ):
        st.audio(
            st.session_state.voice_tts_bytes,
            format=st.session_state.get("voice_tts_mime", "audio/mp3"),
        )

    st.divider()

    if interview_mode == "Text":
        _render_text_interview(language, difficulty)
    else:
        from modules.voice_interview import render_voice_interview_ui

        render_voice_interview_ui(language, difficulty)


def _clear_voice_state_on_new_question() -> None:
    """Reset voice session when a new question is generated."""
    for key in ("voice_transcript", "voice_listening", "voice_tts_bytes", "voice_submit_ready"):
        if key in st.session_state:
            if key == "voice_listening":
                st.session_state[key] = False
            elif key in ("voice_transcript",):
                st.session_state[key] = ""
            else:
                st.session_state[key] = None
