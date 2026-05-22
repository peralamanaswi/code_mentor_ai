"""Video processor: extract audio, transcribe with Groq, and sample/OCR frames."""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict


def process_video(file_path: str, filename: str = "video.mp4") -> Dict[str, Any]:
    """Process video file: extract audio, send to Groq Whisper, sample frames every 5s, OCR frames, combine.

    Args:
        file_path: Path to the temporary video file.
        filename: Original filename.

    Returns:
        Dict with combined text, code, error_message, transcript, success, error.
    """
    import cv2
    import numpy as np
    from moviepy.editor import VideoFileClip
    from utils.image_processor import _get_ocr_reader, preprocess_image_for_ocr, clean_ocr_text
    from utils.speech_to_text import process_audio
    from utils.text_extractor import extract_code_from_text, extract_errors_from_text

    transcript = ""
    audio_err = None
    audio_path = None

    # Step 1: Extract audio track
    try:
        clip = VideoFileClip(file_path)
        if clip.audio is not None:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as atmp:
                audio_path = atmp.name

            clip.audio.write_audiofile(audio_path, logger=None, verbose=False)
            clip.close()

            # Step 2: Send audio to Groq Whisper
            res = process_audio(audio_path, "audio.wav")
            if res.get("success"):
                transcript = res.get("transcript", "")
            else:
                audio_err = res.get("error", "Transcription failed")
        else:
            clip.close()
            audio_err = "No audio track found in video."
    except Exception as exc:
        audio_err = f"Audio extraction/transcription failed: {exc}"
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except OSError:
                pass

    # Step 3 & 4: Extract frames every 5 seconds and run OCR
    ocr_frame_texts = []
    video_err = None

    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            video_err = "Could not open video file for frame extraction."
        else:
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0 or np.isnan(fps):
                fps = 30.0  # Fallback FPS

            # Sample frame interval (every 5 seconds)
            frame_interval = int(fps * 5)
            frame_idx = 0
            extracted_count = 0
            max_frames = 60  # Safeguard: up to 5 minutes of video (60 frames)

            reader = _get_ocr_reader()

            while cap.isOpened() and extracted_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_interval == 0:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as ftmp:
                        ftmp_name = ftmp.name

                    try:
                        cv2.imwrite(ftmp_name, frame)
                        enhanced_img = preprocess_image_for_ocr(ftmp_name)
                        results = reader.readtext(enhanced_img, detail=0, paragraph=True)
                        frame_text = "\n".join(str(r) for r in results if r).strip()
                        frame_text = clean_ocr_text(frame_text)

                        if frame_text and frame_text != "No text detected in image":
                            ocr_frame_texts.append(frame_text)
                            extracted_count += 1
                    finally:
                        if os.path.exists(ftmp_name):
                            try:
                                os.unlink(ftmp_name)
                            except OSError:
                                pass

                frame_idx += 1
            cap.release()
    except Exception as exc:
        video_err = f"Frame OCR failed: {exc}"

    # Step 5: Combine Speech Transcript and OCR Text
    combined_parts = []
    if transcript and transcript != "No speech detected":
        combined_parts.append(f"--- Audio Transcript ---\n{transcript}")
    if ocr_frame_texts:
        combined_parts.append("--- Extracted Text from Video Frames ---\n" + "\n\n".join(ocr_frame_texts))

    combined_text = "\n\n".join(combined_parts).strip()

    if not combined_text:
        err = "Could not extract speech or text from video."
        if audio_err or video_err:
            err += f" Details: [Audio: {audio_err}] [Video: {video_err}]"
        return {
            "text": "No content detected in video",
            "code": "",
            "error_message": "",
            "transcript": "",
            "success": False,
            "error": err,
            "source": "video",
            "filename": filename,
        }

    code = extract_code_from_text(combined_text)
    err_msg = extract_errors_from_text(combined_text)

    return {
        "text": combined_text,
        "code": code,
        "error_message": err_msg,
        "transcript": transcript,
        "success": True,
        "error": None,
        "source": "video",
        "filename": filename,
        "frame_snippets": ocr_frame_texts[:5],
    }
