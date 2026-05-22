"""Record microphone audio with sounddevice (works with Start/Stop buttons)."""

from __future__ import annotations

import io
from typing import List, Optional

import numpy as np

SAMPLE_RATE = 16000
CHANNELS = 1


def frames_to_wav_bytes(frames: List[np.ndarray], sample_rate: int = SAMPLE_RATE) -> bytes:
    """Convert recorded frames to WAV bytes."""
    import scipy.io.wavfile as wav

    if not frames:
        return b""
    audio = np.concatenate(frames, axis=0)
    if audio.ndim > 1:
        audio = audio[:, 0]
    # Normalize float32/int to int16
    if audio.dtype == np.float32 or audio.dtype == np.float64:
        audio = np.clip(audio, -1.0, 1.0)
        audio = (audio * 32767).astype(np.int16)
    buf = io.BytesIO()
    wav.write(buf, sample_rate, audio)
    return buf.getvalue()


def record_fixed_duration(seconds: int = 15, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Block and record for a fixed number of seconds.

    Args:
        seconds: Max recording length.
        sample_rate: Audio sample rate.

    Returns:
        WAV file bytes.
    """
    import sounddevice as sd

    frames = []
    try:
        recording = sd.rec(
            int(seconds * sample_rate),
            samplerate=sample_rate,
            channels=CHANNELS,
            dtype="float32",
        )
        sd.wait()
        frames.append(recording)
    except Exception as exc:
        raise RuntimeError(
            f"Microphone error: {exc}. Check that a mic is connected and allowed in Windows settings."
        ) from exc

    return frames_to_wav_bytes(frames, sample_rate)


def list_input_devices() -> str:
    """Return human-readable list of input devices for debugging."""
    try:
        import sounddevice as sd

        return str(sd.query_devices())
    except Exception as exc:
        return f"Could not list devices: {exc}"
