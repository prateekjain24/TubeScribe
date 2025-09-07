from __future__ import annotations

"""Audio chunking utilities for long files.

Provides helpers to compute chunk boundaries and slice WAV audio using ffmpeg.
Default strategy: fixed windows with small overlaps.
"""

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import List, Tuple

from .audio import ensure_ffmpeg, FFmpegError


@dataclass(frozen=True)
class AudioChunk:
    index: int
    start: float
    end: float
    path: Path


def compute_chunks(duration: float, *, window_seconds: float = 600.0, overlap_seconds: float = 2.0) -> List[Tuple[float, float]]:
    """Compute [start,end] pairs covering `duration` with window size and overlap.

    Ensures 0 <= start < end <= duration and that each subsequent chunk starts
    at (prev_end - overlap).
    """
    if duration <= 0:
        return []
    w = max(1.0, float(window_seconds))
    o = max(0.0, min(float(overlap_seconds), w - 0.001))
    chunks: List[Tuple[float, float]] = []
    start = 0.0
    while start < duration:
        end = min(duration, start + w)
        if end <= start:
            break
        chunks.append((round(start, 3), round(end, 3)))
        if end >= duration:
            break
        start = max(0.0, end - o)
    return chunks


def slice_wav_segment(src: Path, dst: Path, *, start: float, end: float) -> Path:
    """Slice a WAV file into [start,end] seconds using ffmpeg and re-encode to PCM.

    Produces 16 kHz mono PCM WAV similar to normalization settings.
    """
    ensure_ffmpeg()
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        raise FFmpegError(f"source file not found: {src}")
    if end <= start:
        raise FFmpegError("invalid slice bounds: end must be > start")
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Use -ss before -i for fast seek; re-encode for correctness
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{max(0.0, float(start)):.3f}",
        "-to",
        f"{max(0.0, float(end)):.3f}",
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
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(f"ffmpeg slice failed: {proc.stderr.strip()}")
    if not dst.exists():
        raise FFmpegError("ffmpeg reported success but output is missing")
    return dst


__all__ = [
    "AudioChunk",
    "compute_chunks",
    "slice_wav_segment",
]

