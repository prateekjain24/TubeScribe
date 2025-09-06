from __future__ import annotations

from pathlib import Path
from typing import Final
import os
import tempfile

from . import Exporter
from ..models import TranscriptDoc


def s_to_srt_time(t: float) -> str:
    """Convert seconds to SRT time format HH:MM:SS,mmm.

    Rounds milliseconds and clamps negatives to 0.
    """
    if t < 0:
        t = 0.0
    ms = int(round((t - int(t)) * 1000))
    secs = int(t)
    # Carry if rounding pushes ms to 1000
    if ms == 1000:
        secs += 1
        ms = 0
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def s_to_vtt_time(t: float) -> str:
    """Convert seconds to VTT time format HH:MM:SS.mmm."""
    if t < 0:
        t = 0.0
    ms = int(round((t - int(t)) * 1000))
    secs = int(t)
    if ms == 1000:
        secs += 1
        ms = 0
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def write_atomic(path: Path, data: bytes) -> Path:
    """Write bytes atomically to `path` by using a temporary file + rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create temp in the same directory to ensure atomic rename across filesystems
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)
    return path


class FileExporter(Exporter):
    """Base file exporter with path helpers and atomic writes."""

    # Child classes must define `name` and `extension`.
    name: str
    extension: str

    def target_path(self, doc: TranscriptDoc, out_dir: Path) -> Path:
        return Path(out_dir) / f"{doc.video_id}{self.extension}"

    def export(self, doc: TranscriptDoc, out_dir: Path) -> Path:  # pragma: no cover - abstract-ish
        raise NotImplementedError


__all__ = [
    "s_to_srt_time",
    "s_to_vtt_time",
    "write_atomic",
    "FileExporter",
]

