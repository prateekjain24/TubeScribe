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
    ) -> None:
        self.frontmatter = frontmatter
        self.link_style = link_style
        self.include_transcript = include_transcript
        self.include_chapters = include_chapters
        self.template = template

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
        if self.include_chapters and (doc.chapters or []):
            lines: list[str] = []
            for ch in (doc.chapters or []):
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


__all__ = ["MarkdownExporter"]

