from __future__ import annotations

"""Audio utilities: ffmpeg wrappers and helpers."""

import shutil
import subprocess
from pathlib import Path
from typing import Sequence


class FFmpegError(RuntimeError):
    pass


class FFmpegNotFound(RuntimeError):
    pass


def ensure_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise FFmpegNotFound("ffmpeg is required but not found on PATH")


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


__all__ = [
    "FFmpegError",
    "FFmpegNotFound",
    "ensure_ffmpeg",
    "build_normalize_wav_command",
    "normalize_wav",
]

