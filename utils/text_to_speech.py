"""Text-to-speech for reading interview questions aloud (gTTS + pyttsx3)."""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple


def text_to_speech_bytes(text: str, lang: str = "en") -> Tuple[Optional[bytes], str, Optional[str]]:
    """Convert question text to audio bytes for Streamlit playback.

    Tries gTTS (online) first, then pyttsx3 (offline).

    Args:
        text: Question to speak.
        lang: Language code for gTTS.

    Returns:
        Tuple of (audio_bytes, mime_type, error_message).
    """
    if not (text or "").strip():
        return None, "audio/mp3", "No text to speak."

    cleaned = text.strip()[:500]

    # Preferred: gTTS (free)
    try:
        from gtts import gTTS

        buf = io.BytesIO()
        gTTS(text=cleaned, lang=lang).write_to_fp(buf)
        buf.seek(0)
        return buf.read(), "audio/mp3", None
    except Exception as gtts_exc:
        gtts_error = str(gtts_exc)

    # Fallback: pyttsx3 offline
    try:
        import pyttsx3

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()

        engine = pyttsx3.init()
        engine.save_to_file(cleaned, tmp_path)
        engine.runAndWait()

        data = Path(tmp_path).read_bytes()
        os.unlink(tmp_path)
        return data, "audio/wav", None
    except Exception as pyttsx_exc:
        return None, "audio/mp3", f"TTS unavailable (gTTS: {gtts_error}; offline: {pyttsx_exc})"
