"""Speech-to-text transcription using the Groq Whisper API (whisper-large-v3)."""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict


def process_audio(file_path: str, filename: str = "audio.mp3") -> Dict[str, Any]:
    """Convert audio file to text using the Groq Whisper API.

    Args:
        file_path: Path to the temporary audio file.
        filename: Original filename.

    Returns:
        Dict with text, transcript, success, error.
    """
    _, ext = os.path.splitext(filename.lower())
    if ext not in (".mp3", ".wav", ".m4a"):
        return {
            "text": "",
            "code": "",
            "error_message": "",
            "transcript": "",
            "success": False,
            "error": f"Unsupported audio format: '{ext}'. Supported formats: .mp3, .wav, .m4a",
        }

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        return {
            "text": "",
            "code": "",
            "error_message": "",
            "transcript": "",
            "success": False,
            "error": "Groq API key not set or invalid. Please configure GROQ_API_KEY in your .env file.",
        }

    try:
        from groq import Groq

        client = Groq(api_key=api_key)

        with open(file_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(filename, f.read()),
                model="whisper-large-v3",
            )

        transcript = (transcription.text or "").strip()
        if not transcript:
            return {
                "text": "No speech detected",
                "code": "",
                "error_message": "",
                "transcript": "No speech detected",
                "success": False,
                "error": "No speech detected",
                "source": "audio_whisper",
                "filename": filename,
            }

        return {
            "text": transcript,
            "code": "",
            "error_message": "",
            "transcript": transcript,
            "success": True,
            "error": None,
            "source": "audio_whisper",
            "filename": filename,
        }

    except Exception as exc:
        return {
            "text": "",
            "code": "",
            "error_message": "",
            "transcript": "",
            "success": False,
            "error": f"Audio transcription failed: {exc}",
        }


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str = "recording.wav",
) -> Dict[str, Any]:
    """Convert recorded microphone audio bytes to text.

    Args:
        audio_bytes: Raw audio bytes.
        filename: Filename hint.

    Returns:
        Dict with transcript, success, error.
    """
    if not audio_bytes:
        return {
            "transcript": "",
            "success": False,
            "error": "No audio data recorded. Please speak and try again.",
        }

    _, ext = os.path.splitext(filename.lower())
    if not ext:
        ext = ".wav"

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            temp_file_path = tmp.name

        res = process_audio(temp_file_path, filename)
        return {
            "transcript": res.get("transcript", ""),
            "success": res.get("success", False),
            "error": res.get("error"),
        }
    except Exception as exc:
        return {
            "transcript": "",
            "success": False,
            "error": f"Audio processing failed: {exc}",
        }
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
