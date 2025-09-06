from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import textwrap

import srt

from . import register_exporter
from .base import FileExporter, write_atomic
from ..models import TranscriptDoc


def _normalize_spaces(text: str) -> str:
    return " ".join(text.split())


def wrap_caption(text: str, *, line_width: int = 42, max_lines: int = 2) -> str:
    """Wrap caption text to at most `max_lines` lines with ~`line_width` chars.

    Uses whitespace boundaries; does not break long words. If wrapping would
    exceed `max_lines`, the remainder is placed on the last line.
    """
    text = _normalize_spaces(text)
    if not text:
        return ""
    lines = textwrap.wrap(
        text,
        width=max(16, line_width),
        break_long_words=False,
        break_on_hyphens=False,
    )
    if len(lines) <= max_lines:
        return "\n".join(lines)
    head = lines[: max_lines - 1]
    tail = " ".join(lines[max_lines - 1 :])
    return "\n".join([*head, tail])


@register_exporter
class SRTExporter(FileExporter):
    name = "srt"
    extension = ".srt"

    def __init__(self, *, line_width: int = 42, max_lines: int = 2) -> None:
        self.line_width = line_width
        self.max_lines = max_lines

    def export(self, doc: TranscriptDoc, out_dir: Path) -> Path:
        path = self.target_path(doc, out_dir)
        subs: list[srt.Subtitle] = []
        prev_end = 0.0
        for seg in doc.segments:
            start = max(seg.start, prev_end)
            end = max(seg.end, start + 0.001)
            prev_end = end
            content = wrap_caption(seg.text, line_width=self.line_width, max_lines=self.max_lines)
            if not content.strip():
                continue  # skip empty captions
            subs.append(
                srt.Subtitle(
                    index=len(subs) + 1,
                    start=timedelta(seconds=start),
                    end=timedelta(seconds=end),
                    content=content,
                )
            )

        data = srt.compose(subs).encode("utf-8")
        return write_atomic(path, data)


__all__ = ["SRTExporter", "wrap_caption"]
