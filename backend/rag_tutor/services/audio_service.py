"""
Local audio transcription for multimodal RAG.

Uses faster-whisper when installed. No paid or hosted API is called.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

_whisper_model = None


def _ensure_ffmpeg_on_path() -> None:
    """
    faster-whisper needs an ffmpeg executable. If the machine does not ship one,
    fall back to the binary bundled by imageio-ffmpeg.
    """
    try:
        import imageio_ffmpeg  # noqa: PLC0415
    except ImportError:
        return

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = str(Path(ffmpeg_exe).parent)
    path = os.environ.get("PATH", "")
    if ffmpeg_dir and ffmpeg_dir not in path:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + path


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    try:
        from faster_whisper import WhisperModel  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "Audio transcription requires faster-whisper. "
            "Install it with: pip install faster-whisper"
        ) from exc

    model_name = os.getenv("WHISPER_MODEL", "base")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    _ensure_ffmpeg_on_path()
    logger.info(
        "Loading faster-whisper model=%s device=%s compute_type=%s",
        model_name,
        device,
        compute_type,
    )
    _whisper_model = WhisperModel(model_name, device=device, compute_type=compute_type)
    return _whisper_model


def _suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix else ".audio"


def transcribe_audio(filename: str, audio_bytes: bytes) -> Dict:
    """
    Transcribe audio bytes into timestamped text segments.

    Returns:
        {
            "text": str,
            "segments": [{"text": str, "start": float, "end": float}],
            "metadata": {...}
        }
    """
    model = _get_whisper_model()

    with tempfile.NamedTemporaryFile(suffix=_suffix(filename), delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments_iter, info = model.transcribe(
            tmp_path,
            beam_size=1,
            vad_filter=True,
            word_timestamps=False,
        )
        segments: List[Dict] = []
        for seg in segments_iter:
            text = (seg.text or "").strip()
            if not text:
                continue
            segments.append({
                "text": text,
                "start": round(float(seg.start), 2),
                "end": round(float(seg.end), 2),
            })

        full_text = "\n".join(s["text"] for s in segments)
        metadata = {
            "filename": filename,
            "language": getattr(info, "language", None),
            "language_probability": round(float(getattr(info, "language_probability", 0.0)), 3),
            "duration": round(float(getattr(info, "duration", 0.0)), 2),
            "model": os.getenv("WHISPER_MODEL", "base"),
        }
        return {"text": full_text, "segments": segments, "metadata": metadata}
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
