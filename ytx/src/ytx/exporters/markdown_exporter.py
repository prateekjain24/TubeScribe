from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Literal

from . import register_exporter
from .base import FileExporter, write_atomic
from ..models import TranscriptDoc
from .utils import seconds_to_hhmmss, youtube_url, safe_md


@register_exporter
class MarkdownExporter(FileExporter):
    name = "md"
    extension = ".md"

    def __init__(
        self,
        *,
        frontmatter: bool = False,
        link_style: Literal["short", "long"] = "short",
        include_transcript: bool = False,
        include_chapters: bool = True,
        template: Path | None = None,
        auto_chapter_every_sec: float | None = None,
    ) -> None:
        self.frontmatter = frontmatter
        self.link_style = link_style
        self.include_transcript = include_transcript
        self.include_chapters = include_chapters
        self.template = template
        self.auto_chapter_every_sec = auto_chapter_every_sec

    def export(self, doc: TranscriptDoc, out_dir: Path) -> Path:
        content = self._render(doc)
        return write_atomic(self.target_path(doc, out_dir), content.encode("utf-8"))

    # --- rendering ---
    def _render(self, doc: TranscriptDoc) -> str:
        # Optional user template support (simple passthrough in v1)
        if self.template:
            try:
                raw = Path(self.template).read_text(encoding="utf-8")
                # Minimal token replacement; safe and predictable
                return (
                    raw.replace("{{title}}", (doc.title or doc.video_id))
                    .replace("{{url}}", self._video_url(doc))
                    .replace("{{video_id}}", doc.video_id)
                )
            except Exception:
                # Fall through to default rendering
                pass

        parts: list[str] = []
        if self.frontmatter:
            parts.append(self._render_frontmatter(doc))
        # Title header with link
        title = doc.title or doc.video_id
        url = self._video_url(doc)
        parts.append(f"# [{safe_md(title)}]({url})")

        # Summary
        if getattr(doc, "summary", None):
            tldr = (getattr(doc.summary, "tldr", "") or "").strip()
            bullets = list(getattr(doc.summary, "bullets", []) or [])
            if tldr:
                parts.append("\n## Summary\n" + tldr)
            if bullets:
                parts.append("\n## Key Points\n" + "\n".join(f"- {safe_md(b)}" for b in bullets if b))

        # Chapters
        if self.include_chapters:
            # Use chapters from doc, or synthesize if requested
            chapters = list(doc.chapters or [])
            if not chapters and self.auto_chapter_every_sec and getattr(doc, "duration", None):
                chapters = self._auto_chapters(doc)
            lines: list[str] = []
            for ch in chapters:
                start = seconds_to_hhmmss(float(getattr(ch, "start", 0.0) or 0.0))
                when = float(getattr(ch, "start", 0.0) or 0.0)
                link = youtube_url(doc.video_id, when, style=self.link_style)
                title = getattr(ch, "title", None) or "Chapter"
                lines.append(f"### [{start}]({link}) {safe_md(title)}")
            if lines:
                parts.append("\n## Chapters\n" + "\n".join(lines))

        # Optional transcript (disabled by default)
        if self.include_transcript and (doc.segments or []):
            seg_lines: list[str] = []
            for s in doc.segments:
                ts = seconds_to_hhmmss(float(getattr(s, "start", 0.0) or 0.0))
                seg_lines.append(f"- [{ts}] {safe_md(getattr(s, 'text', '') or '')}")
            if seg_lines:
                parts.append("\n## Transcript\n" + "\n".join(seg_lines))

        return "\n\n".join([p for p in parts if p]) + "\n"

    def _render_frontmatter(self, doc: TranscriptDoc) -> str:
        title = (doc.title or doc.video_id)
        url = self._video_url(doc)
        dur = seconds_to_hhmmss(float(doc.duration or 0.0)) if getattr(doc, "duration", None) is not None else ""
        date = self._date_iso(doc)
        engine = doc.engine
        model = doc.model
        lines = [
            "---",
            f"title: {title}",
            f"url: {url}",
            f"date: {date}",
            f"duration: {dur}",
            f"engine: {engine}",
            f"model: {model}",
            "tags: [youtube, transcript]",
            "---",
            "",
        ]
        return "\n".join(lines)

    def _video_url(self, doc: TranscriptDoc) -> str:
        try:
            return youtube_url(doc.video_id, None, style=self.link_style)
        except Exception:
            return doc.source_url

    def _date_iso(self, doc: TranscriptDoc) -> str:
        try:
            dt = getattr(doc, "created_at", None)
            if isinstance(dt, datetime):
                return dt.date().isoformat()
        except Exception:
            pass
        return datetime.utcnow().date().isoformat()

    # --- synthesize simple chapters ---
    def _auto_chapters(self, doc: TranscriptDoc):  # type: ignore[no-untyped-def]
        try:
            total = float(getattr(doc, "duration", 0.0) or 0.0)
        except Exception:
            total = 0.0
        interval = float(self.auto_chapter_every_sec or 0.0)
        if total <= 0.0 or interval <= 0.0:
            return []
        starts: list[float] = []
        t = 0.0
        while t < total:
            starts.append(t)
            t += interval
        # Ensure last starts not beyond total; no explicit end used for rendering
        class _C:
            def __init__(self, title: str, start: float, end: float) -> None:
                self.title = title
                self.start = start
                self.end = end

        out = []
        for i, s in enumerate(starts, start=1):
            e = min(total, s + interval)
            out.append(_C(title=f"Part {i}", start=s, end=e))
        return out


__all__ = ["MarkdownExporter"]
