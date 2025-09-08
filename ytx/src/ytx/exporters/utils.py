from __future__ import annotations

"""Helper utilities for exporters (time formatting, links, minimal escaping)."""

from typing import Literal


def seconds_to_hhmmss(seconds: float) -> str:
    """Format seconds as H:MM:SS or M:SS with floor semantics.

    - Floors fractional seconds (83.9 -> 83)
    - < 1 hour: M:SS (no leading 0 for minutes)
    - >= 1 hour: H:MM:SS
    - Negative values are clamped to 0.
    """
    if seconds is None:
        seconds = 0.0
    try:
        s = int(seconds)
    except Exception:
        s = 0
    if s < 0:
        s = 0
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def youtube_url(
    video_id: str,
    seconds: float | None = None,
    *,
    style: Literal["short", "long"] = "short",
) -> str:
    """Return a YouTube URL for a video with optional start time.

    - style="short" → https://youtu.be/<id>
    - style="long" → https://www.youtube.com/watch?v=<id>
    - Adds ?t=<seconds> (floored) when seconds > 0.
    - Seconds <= 0 or None omits the t parameter.
    """
    vid = (video_id or "").strip()
    base = (
        f"https://youtu.be/{vid}" if style == "short" else f"https://www.youtube.com/watch?v={vid}"
    )
    if seconds is None:
        return base
    try:
        t = int(seconds)
    except Exception:
        t = 0
    if t <= 0:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}t={t}"


def safe_md(text: str) -> str:
    """Minimal Markdown escaping for inline text.

    This is intentionally conservative; headings and code blocks should be
    constructed explicitly by exporters.
    """
    if text is None:
        return ""
    # Escape a few common special characters inline
    out = (
        text.replace("*", "\\*")
        .replace("_", "\\_")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("(`", "(\\`")
        .replace("`)", "\\`)")
    )
    return out


__all__ = ["seconds_to_hhmmss", "youtube_url", "safe_md"]

