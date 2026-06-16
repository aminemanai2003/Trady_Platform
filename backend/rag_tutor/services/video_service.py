"""
Local video extraction for multimodal RAG.

Videos become text-grounded evidence through:
1. Audio track extraction + faster-whisper transcription.
2. Sampled frame OCR / local vision extraction.

No hosted or paid API is called.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List

from .audio_service import _ensure_ffmpeg_on_path, transcribe_audio
from .image_service import extract_image_evidence

logger = logging.getLogger(__name__)

_FRAME_INTERVAL_SECONDS = 30
_MAX_FRAMES = 20


def _ffmpeg_exe() -> str:
    _ensure_ffmpeg_on_path()
    try:
        import imageio_ffmpeg  # noqa: PLC0415
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return "ffmpeg"


def _suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix else ".video"


def _run_ffmpeg(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_ffmpeg_exe(), "-hide_banner", "-nostdin", *args],
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )


def _extract_audio_track(video_path: str, workdir: str) -> tuple[str | None, str]:
    audio_path = str(Path(workdir) / "audio.wav")
    result = _run_ffmpeg(
        [
            "-y",
            "-i",
            video_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            audio_path,
        ],
        timeout=240,
    )
    if result.returncode != 0 or not Path(audio_path).exists() or Path(audio_path).stat().st_size == 0:
        return None, (result.stderr or result.stdout or "").strip()
    return audio_path, ""


def _sample_frames(video_path: str, workdir: str) -> tuple[list[Path], str]:
    frames_dir = Path(workdir) / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    frames: list[Path] = []

    for index in range(_MAX_FRAMES):
        timestamp = index * _FRAME_INTERVAL_SECONDS
        frame_path = frames_dir / f"frame_{index:04d}.png"
        result = _run_ffmpeg(
            [
                "-y",
                "-ss",
                str(timestamp),
                "-i",
                video_path,
                "-frames:v",
                "1",
                str(frame_path),
            ],
            timeout=90,
        )
        if frame_path.exists() and frame_path.stat().st_size > 0:
            frames.append(frame_path)
            continue

        errors.append((result.stderr or result.stdout or "").strip())
        if index > 0:
            break

    if not frames:
        return [], "\n".join(e for e in errors if e)[-2000:]
    return frames, "\n".join(e for e in errors if e)[-2000:]


def _transcript_segments(filename: str, audio_path: str) -> tuple[list[Dict], Dict]:
    with open(audio_path, "rb") as audio_file:
        result = transcribe_audio(f"{filename}.audio.wav", audio_file.read())

    segments = []
    for seg in result.get("segments", []):
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        segments.append(
            {
                "text": text,
                "start": seg.get("start"),
                "end": seg.get("end"),
                "metadata": {
                    "kind": "audio_transcript",
                    "timestamp_start": seg.get("start"),
                    "timestamp_end": seg.get("end"),
                },
            }
        )
    return segments, result.get("metadata", {})


def _frame_segments(filename: str, frames: list[Path]) -> list[Dict]:
    segments: List[Dict] = []
    for index, frame_path in enumerate(frames):
        timestamp = float(index * _FRAME_INTERVAL_SECONDS)
        try:
            evidence = extract_image_evidence(
                f"{filename} frame {timestamp:.0f}s",
                frame_path.read_bytes(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Video frame extraction skipped frame=%s: %s", frame_path.name, exc)
            continue

        text = str(evidence.get("text", "")).strip()
        if not text:
            continue
        segments.append(
            {
                "text": f"VIDEO FRAME AT {timestamp:.1f}s:\n{text}",
                "start": timestamp,
                "end": timestamp,
                "metadata": {
                    "kind": "sampled_frame",
                    "frame_index": index,
                    "timestamp_start": timestamp,
                    "timestamp_end": timestamp,
                    "frame_extraction": evidence.get("metadata", {}),
                },
            }
        )
    return segments


def extract_video_evidence(filename: str, video_bytes: bytes) -> Dict:
    """
    Extract timestamped text evidence from a local video upload.

    Returns:
        {
            "segments": [{"text": str, "start": float, "end": float, "metadata": dict}],
            "metadata": {...}
        }
    """
    with tempfile.TemporaryDirectory(prefix="rag_video_") as workdir:
        video_path = str(Path(workdir) / f"upload{_suffix(filename)}")
        with open(video_path, "wb") as video_file:
            video_file.write(video_bytes)

        segments: List[Dict] = []
        metadata: Dict = {
            "filename": filename,
            "modality": "video",
            "frame_interval_seconds": _FRAME_INTERVAL_SECONDS,
            "max_frames": _MAX_FRAMES,
            "audio": {"available": False},
            "frames": {"count": 0},
        }

        audio_path, audio_error = _extract_audio_track(video_path, workdir)
        if audio_path:
            try:
                transcript, transcript_meta = _transcript_segments(filename, audio_path)
                segments.extend(transcript)
                metadata["audio"] = {
                    "available": True,
                    "segments": len(transcript),
                    "transcription": transcript_meta,
                }
            except Exception as exc:  # noqa: BLE001
                metadata["audio"] = {"available": True, "error": str(exc)}
                logger.warning("Video audio transcription failed for %s: %s", filename, exc)
        else:
            metadata["audio"] = {"available": False, "error": audio_error[:1000]}

        frames, frame_error = _sample_frames(video_path, workdir)
        if frames:
            frame_segments = _frame_segments(filename, frames)
            segments.extend(frame_segments)
            metadata["frames"] = {
                "count": len(frames),
                "indexed_segments": len(frame_segments),
            }
        else:
            metadata["frames"] = {"count": 0, "error": frame_error[:1000]}

        if not segments:
            raise RuntimeError(
                "No transcript or readable frame evidence could be extracted from this video. "
                "Try a video with clearer speech, slides, captions, or visible text."
            )

        return {"segments": segments, "metadata": metadata}
