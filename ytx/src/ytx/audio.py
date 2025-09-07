from __future__ import annotations

"""Audio utilities: ffmpeg/ffprobe wrappers and helpers."""

import shutil
import subprocess
from pathlib import Path


from .errors import FileSystemError


class FFmpegError(FileSystemError):
    pass


class FFmpegNotFound(FileSystemError):
    pass


def ensure_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise FFmpegNotFound("ffmpeg is required but not found on PATH")


def ensure_ffprobe() -> None:
    if not shutil.which("ffprobe"):
        raise FFmpegNotFound("ffprobe is required but not found on PATH")


def build_normalize_wav_command(src: Path, dst: Path) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]


def normalize_wav(src: Path, dst: Path, *, overwrite: bool = False) -> Path:
    """Convert input audio to 16 kHz mono PCM WAV using ffmpeg."""
    ensure_ffmpeg()
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not overwrite:
        return dst

    cmd = build_normalize_wav_command(src, dst)
    try:
        proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    except Exception as e:  # pragma: no cover
        raise FFmpegError(f"ffmpeg execution failed: {e}")
    if proc.returncode != 0:
        raise FFmpegError(f"ffmpeg failed: {proc.stderr.strip()}")
    if not dst.exists():
        raise FFmpegError("ffmpeg reported success but output file is missing")
    return dst


def build_ffprobe_duration_command(path: Path) -> list[str]:
    return [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]


def probe_duration(path: Path) -> float:
    """Return duration in seconds using ffprobe.

    Raises FFmpegError if duration cannot be determined.
    """
    ensure_ffprobe()
    path = Path(path)
    if not path.exists():
        raise FFmpegError(f"file does not exist: {path}")
    cmd = build_ffprobe_duration_command(path)
    try:
        proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    except Exception as e:  # pragma: no cover
        raise FFmpegError(f"ffprobe execution failed: {e}")
    if proc.returncode != 0:
        raise FFmpegError(f"ffprobe failed: {proc.stderr.strip()}")
    out = (proc.stdout or "").strip()
    try:
        val = float(out)
    except Exception as e:
        raise FFmpegError(f"invalid ffprobe duration: {out!r}") from e
    if not (val >= 0):
        raise FFmpegError(f"negative duration reported: {val}")
    return float(val)


__all__ = [
    "FFmpegError",
    "FFmpegNotFound",
    "ensure_ffmpeg",
    "ensure_ffprobe",
    "build_normalize_wav_command",
    "normalize_wav",
    "build_ffprobe_duration_command",
    "probe_duration",
]
