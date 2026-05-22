"""Audio speech-to-text using OpenAI Whisper (with fallback)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

_WHISPER_MODEL: Optional[Any] = None


def _load_whisper_model():
    """Load Whisper model once (tiny = faster for Streamlit)."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        import whisper

        _WHISPER_MODEL = whisper.load_model("tiny")
    return _WHISPER_MODEL


def process_audio(audio_bytes: bytes, filename: str = "audio.mp3") -> Dict[str, Any]:
    """Convert speech to text and detect coding questions.

    Args:
        audio_bytes: Raw audio file bytes.
        filename: Original filename.

    Returns:
        Dict with transcript in text/transcript fields.
    """
    suffix = Path(filename).suffix or ".mp3"
    transcript = ""
    error_notes: list[str] = []

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        transcript = _transcribe_whisper(tmp_path)
    except Exception as exc:
        error_notes.append(f"Whisper: {exc}")
        try:
            transcript = _transcribe_speech_recognition(tmp_path)
        except Exception as exc2:
            error_notes.append(f"SpeechRecognition: {exc2}")

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if not transcript.strip():
        return {
            "text": "",
            "code": "",
            "error_message": "",
            "transcript": "",
            "success": False,
            "error": "Could not transcribe audio. " + "; ".join(error_notes),
        }

    return {
        "text": transcript,
        "code": "",
        "error_message": "",
        "transcript": transcript,
        "success": True,
        "error": error_notes[0] if error_notes and "Whisper" in error_notes[0] else None,
        "source": "audio_whisper",
        "filename": filename,
    }


def _transcribe_whisper(path: str) -> str:
    """Transcribe using openai-whisper."""
    model = _load_whisper_model()
    result = model.transcribe(path, fp16=False)
    return (result.get("text") or "").strip()


def _transcribe_speech_recognition(path: str) -> str:
    """Fallback transcription via SpeechRecognition."""
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    with sr.AudioFile(path) as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio)
