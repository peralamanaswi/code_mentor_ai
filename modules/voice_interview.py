"""Voice Interview Mode – TTS questions, microphone answers, AI evaluation."""

from __future__ import annotations

import streamlit as st

from utils.helper import render_card, show_toast
from utils.microphone_recorder import (
    SAMPLE_RATE,
    frames_to_wav_bytes,
    record_fixed_duration,
)
from utils.speech_to_text import transcribe_audio_bytes
from utils.text_to_speech import text_to_speech_bytes


def _init_voice_state() -> None:
    """Initialize session keys for voice interview."""
    defaults = {
        "voice_listening": False,
        "voice_transcript": "",
        "voice_audio_bytes": None,
        "voice_tts_bytes": None,
        "voice_tts_mime": "audio/mp3",
        "voice_frames": None,
        "voice_input_stream": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _stop_input_stream() -> None:
    """Stop and close the active sounddevice stream."""
    stream = st.session_state.get("voice_input_stream")
    if stream is not None:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
    st.session_state.voice_input_stream = None
    st.session_state.voice_listening = False


def _clear_voice_answer() -> None:
    """Reset recording and transcript for retry."""
    _stop_input_stream()
    st.session_state.voice_transcript = ""
    st.session_state.voice_audio_bytes = None
    st.session_state.voice_frames = []


def _make_audio_callback(frame_buffer: list):
    """Build callback that appends frames (thread-safe list)."""

    def callback(indata, _frames, _time, status):
        if status:
            st.session_state.voice_rec_status = str(status)
        frame_buffer.append(indata.copy())

    return callback


def _start_microphone() -> Optional[str]:
    """Start live microphone capture. Returns error message or None."""
    import sounddevice as sd

    try:
        _stop_input_stream()
        st.session_state.voice_frames = []
        st.session_state.voice_frame_buffer = []
        st.session_state.voice_audio_bytes = None
        st.session_state.voice_transcript = ""

        callback = _make_audio_callback(st.session_state.voice_frame_buffer)
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=callback,
        )
        stream.start()
        st.session_state.voice_input_stream = stream
        st.session_state.voice_listening = True
        return None
    except Exception as exc:
        return (
            f"Could not open microphone: {exc}. "
            "Allow mic access in Windows Settings → Privacy → Microphone."
        )


def _finalize_recording() -> Optional[str]:
    """Stop stream and save WAV bytes. Returns error or None."""
    _stop_input_stream()
    frames = (
        st.session_state.get("voice_frame_buffer")
        or st.session_state.get("voice_frames")
        or []
    )
    if not frames:
        return "No audio captured. Click Start Recording, speak, then Stop Recording."

    wav_bytes = frames_to_wav_bytes(frames)
    if len(wav_bytes) < 1000:
        return "Recording too short. Please speak for at least 2–3 seconds."

    st.session_state.voice_audio_bytes = wav_bytes
    return None


def speak_question_if_enabled(question: str, enable_voice: bool) -> None:
    """Generate TTS audio and play question when enabled."""
    if not enable_voice or not question:
        return

    with st.spinner("Preparing voice..."):
        audio_bytes, mime, err = text_to_speech_bytes(question)

    if audio_bytes:
        st.session_state.voice_tts_bytes = audio_bytes
        st.session_state.voice_tts_mime = mime
        st.audio(audio_bytes, format=mime)
        st.caption("🔊 Question read aloud. Listen, then record your answer below.")
    elif err:
        st.warning(f"Voice playback unavailable: {err}")


def render_voice_interview_ui(language: str, difficulty: str) -> None:
    """Voice Interview Mode UI – record, transcribe, evaluate."""
    _init_voice_state()
    question = st.session_state.get("interview_question", "")

    if not question:
        st.info("Select a practice question above to start your voice interview.")
        return

    st.markdown(
        f"""
        <div class="hero-card">
            <strong>📋 Interview Question</strong><br/><br/>
            {question}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("#### 🎙️ Record Your Answer")
    st.caption(
        "1. Click **Start Recording** → speak → **Stop Recording** → **Submit Answer**. "
        "Allow microphone access if your browser or Windows asks."
    )

    btn1, btn2, btn3, btn4 = st.columns(4)

    with btn1:
        if st.button("🎤 Start Recording", key="voice_start", use_container_width=True):
            err = _start_microphone()
            if err:
                st.error(err)
            else:
                show_toast("Microphone on — speak now!", "🎙️")
                st.rerun()

    with btn2:
        if st.button("⏹ Stop Recording", key="voice_stop", use_container_width=True):
            err = _finalize_recording()
            if err:
                st.warning(err)
            else:
                show_toast("Recording saved!", "✅")
                st.rerun()

    with btn3:
        if st.button("🔁 Retry Answer", key="voice_retry", use_container_width=True):
            _clear_voice_answer()
            show_toast("Cleared — record again.", "🔄")
            st.rerun()

    with btn4:
        submit_clicked = st.button(
            "✅ Submit Answer",
            key="voice_submit",
            type="primary",
            use_container_width=True,
        )

    if st.session_state.voice_listening:
        st.markdown(
            '<p class="listening-badge">🎙️ <strong>Listening...</strong> '
            "Speak clearly, then click <strong>Stop Recording</strong>.</p>",
            unsafe_allow_html=True,
        )

    # Show saved recording
    if st.session_state.voice_audio_bytes:
        st.audio(st.session_state.voice_audio_bytes, format="audio/wav")
        st.success("Recording captured. Click **Submit Answer** to transcribe and evaluate.")

    if st.session_state.voice_transcript:
        st.markdown("##### Your Answer (Converted to Text)")
        st.info(st.session_state.voice_transcript)

    # Quick record fallback (15 sec auto) if sounddevice stream fails
    with st.expander("Having trouble? Try quick 15-second recording"):
        if st.button("Record 15 seconds now", key="voice_quick_record"):
            try:
                with st.spinner("Recording 15 seconds — speak now!"):
                    st.session_state.voice_audio_bytes = record_fixed_duration(15)
                _stop_input_stream()
                show_toast("15-second recording done!", "✅")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    if submit_clicked:
        # Auto-stop if still listening
        if st.session_state.voice_listening:
            err = _finalize_recording()
            if err:
                st.warning(err)
                return

        audio_bytes = st.session_state.voice_audio_bytes
        if not audio_bytes:
            st.warning(
                "No recording found. Click **Start Recording**, speak, "
                "**Stop Recording**, then **Submit Answer**."
            )
            return

        if not st.session_state.voice_transcript:
            with st.spinner("Converting speech to text..."):
                result = transcribe_audio_bytes(audio_bytes, "recording.wav")
            if not result["success"]:
                st.error(result["error"])
                return
            st.session_state.voice_transcript = result["transcript"]
            st.rerun()

        _run_evaluation(language, difficulty, question, st.session_state.voice_transcript)


def _run_evaluation(language: str, difficulty: str, question: str, transcript: str) -> None:
    """Evaluate voice transcript with AI."""
    from modules.interview_assistant import evaluate_answer, parse_score

    with st.spinner("AI is evaluating your spoken answer..."):
        report = evaluate_answer(
            language,
            difficulty,
            question,
            transcript,
            voice_mode=True,
        )
    score = parse_score(report)
    if score:
        st.metric("Your Score", score)
    show_toast("Voice interview evaluation complete!")
    render_card("📝 Voice Interview Feedback", report)
