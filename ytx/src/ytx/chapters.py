from __future__ import annotations

"""Chapter extraction utilities (from yt-dlp metadata).

Provides helpers to parse chapter metadata emitted by yt-dlp's --dump-json
output into our Chapter model. Handles videos without chapters gracefully.
"""

from typing import Any, List
from dataclasses import dataclass

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
    for it in items:
        start = _parse_time(it.get("start_time") or it.get("start") or it.get("startTime"))
        end = _parse_time(it.get("end_time") or it.get("end") or it.get("endTime"))
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
]

