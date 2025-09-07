from __future__ import annotations

"""Chapter extraction utilities (from yt-dlp metadata).

Provides helpers to parse chapter metadata emitted by yt-dlp's --dump-json
output into our Chapter model. Handles videos without chapters gracefully.
"""

from typing import Any, List, Callable, Tuple
from dataclasses import dataclass
from pathlib import Path
import tempfile

from .chunking import slice_wav_segment
from .models import TranscriptSegment
from .config import AppConfig
from .engines.base import TranscriptionEngine

from .models import Chapter


def _parse_time(v: Any) -> float | None:
    """Parse a chapter time value into seconds.

    Accepts int/float seconds or strings in HH:MM:SS(.mmm) or MM:SS(.mmm).
    Returns None if unparseable.
    """
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        # numeric string
        try:
            return float(s)
        except Exception:
            pass
        parts = s.split(":")
        try:
            parts_f = [float(p) for p in parts]
        except Exception:
            return None
        if len(parts_f) == 3:
            h, m, sec = parts_f
        elif len(parts_f) == 2:
            h, m, sec = 0.0, parts_f[0], parts_f[1]
        else:
            return None
        return float(max(0.0, h * 3600.0 + m * 60.0 + sec))
    return None


def parse_yt_dlp_chapters(data: dict[str, Any], *, video_duration: float | None = None) -> list[Chapter]:
    """Extract chapters from yt-dlp metadata dict.

    Expects a `chapters` list of dicts with keys like `start_time`, `end_time`, and `title`.
    - Computes missing `end_time` using the next chapter's start or the video duration.
    - Filters invalid entries and ensures end > start.
    """
    raw = data.get("chapters")
    if not isinstance(raw, list) or not raw:
        return []
    items: list[dict[str, Any]] = [x for x in raw if isinstance(x, dict)]
    if not items:
        return []
    # Normalize start/end
    norm: list[tuple[float, float | None, str | None]] = []
    def _first_present(d: dict[str, Any], keys: list[str]) -> Any:
        for k in keys:
            if k in d and d[k] is not None:
                return d[k]
        return None

    for it in items:
        start = _parse_time(_first_present(it, ["start_time", "start", "startTime"]))
        end = _parse_time(_first_present(it, ["end_time", "end", "endTime"]))
        title = (it.get("title") or it.get("name") or it.get("chapter") or "").strip() or None
        if start is None:
            continue
        norm.append((start, end, title))
    # Sort by start
    norm.sort(key=lambda t: t[0])
    # Fill missing ends from next start or duration
    result: list[Chapter] = []
    for i, (start, end, title) in enumerate(norm):
        if end is None:
            next_start = norm[i + 1][0] if i + 1 < len(norm) else None
            if next_start is not None and next_start > start:
                end = next_start
            elif video_duration is not None and video_duration > start:
                end = video_duration
            else:
                # Cannot determine end; skip
                continue
        if end <= start:
            continue
        result.append(Chapter(title=title or None, start=float(start), end=float(end)))
    return result


__all__ = [
    "parse_yt_dlp_chapters",
    "slice_audio_by_chapters",
    "process_chapters",
    "offset_chapter_segments",
    "stitch_chapter_segments",
]


def _safe_slug(s: str | None) -> str:
    if not s:
        return "untitled"
    out = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in s.lower())
    out = out.strip("-") or "untitled"
    return out[:40]


def slice_audio_by_chapters(
    src: Path,
    chapters: List[Chapter],
    out_dir: Path,
    *,
    overlap_seconds: float = 2.0,
) -> List[Tuple[int, Chapter, Path]]:
    """Slice `src` WAV into per-chapter WAV files with small overlaps.

    Returns a list of (index, chapter, path) in order.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    items: List[Tuple[int, Chapter, Path]] = []
    n = len(chapters)
    for i, ch in enumerate(chapters):
        # Overlap: add overlap_seconds to the end except the last chapter
        start = float(ch.start)
        end = float(ch.end)
        if i < n - 1:
            end = min(float(chapters[i + 1].end), end + max(0.0, overlap_seconds))
        name = f"chapter_{i:03d}_{_safe_slug(ch.title)}.wav"
        dst = out_dir / name
        slice_wav_segment(src, dst, start=start, end=end)
        items.append((i, ch, dst))
    return items


def process_chapters(
    src: Path,
    chapters: List[Chapter],
    *,
    engine: TranscriptionEngine,
    config: AppConfig,
    overlap_seconds: float = 2.0,
    work_dir: Path | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> List[Tuple[int, Chapter, List[TranscriptSegment]]]:
    """Transcribe each chapter independently and return per-chapter segments.

    Does not adjust segment timestamps to video time (handled in CHAPTER-005).
    Progress callback receives (completed_chapters, total_chapters).
    """
    if not chapters:
        return []
    total = len(chapters)
    cleanup = False
    if work_dir is None:
        tmp = tempfile.TemporaryDirectory(prefix="ytx-chapters-")
        work_dir = Path(tmp.name)
        cleanup = True
    else:
        work_dir.mkdir(parents=True, exist_ok=True)
        tmp = None  # type: ignore
    try:
        parts = slice_audio_by_chapters(src, chapters, work_dir, overlap_seconds=overlap_seconds)
        results: List[Tuple[int, Chapter, List[TranscriptSegment]]] = []
        for idx, (i, ch, path) in enumerate(parts):
            segs = engine.transcribe(path, config=config, on_progress=None)
            results.append((i, ch, segs))
            if on_progress:
                try:
                    on_progress(idx + 1, total)
                except Exception:
                    pass
        # Ensure order by chapter index
        results.sort(key=lambda t: t[0])
        return results
    finally:
        if cleanup and tmp is not None:
            try:
                tmp.cleanup()
            except Exception:
                pass


def offset_chapter_segments(
    items: List[Tuple[int, Chapter, List[TranscriptSegment]]]
) -> List[TranscriptSegment]:
    """Convert per-chapter local segments to global timeline by adding offsets.

    Does not clamp to chapter end; boundary overlaps are resolved in stitching.
    """
    out: List[TranscriptSegment] = []
    for idx, ch, segs in items:
        base = float(ch.start)
        for s in segs:
            out.append(
                TranscriptSegment(
                    id=0,
                    start=float(base) + float(s.start),
                    end=float(base) + float(s.end),
                    text=s.text,
                    confidence=s.confidence,
                )
            )
    # Renumber by time
    out.sort(key=lambda s: (s.start, s.end))
    for i, s in enumerate(out):
        s.id = i
    return out


def stitch_chapter_segments(
    segments: List[TranscriptSegment], *, epsilon: float = 0.01
) -> List[TranscriptSegment]:
    """Stitch overlapping/duplicate segments across chapter boundaries.

    Uses global stitcher and preserves chronological order. Chapter markers are
    not modified (they live in the TranscriptDoc.chapters field).
    """
    from .stitch import stitch_segments

    return stitch_segments(segments, epsilon=epsilon)
