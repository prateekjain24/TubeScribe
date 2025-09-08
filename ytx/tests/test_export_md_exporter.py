from pathlib import Path

from ytx.models import TranscriptDoc, TranscriptSegment, Chapter
from ytx.exporters.markdown_exporter import MarkdownExporter


def make_doc() -> TranscriptDoc:
    segs = [
        TranscriptSegment(id=0, start=0.0, end=0.5, text="Hello world"),
        TranscriptSegment(id=1, start=5.2, end=6.0, text="Bye now"),
    ]
    chs = [Chapter(title="Intro", start=0.0, end=5.0)]
    return TranscriptDoc(
        video_id="ABCDEFGHIJK",
        source_url="https://youtu.be/ABCDEFGHIJK",
        title="Sample",
        duration=6.0,
        language="en",
        engine="whisper",
        model="small",
        segments=segs,
        chapters=chs,
    )


def test_md_exporter_basic(tmp_path: Path):
    doc = make_doc()
    path = MarkdownExporter(frontmatter=False).export(doc, tmp_path)
    txt = path.read_text(encoding="utf-8")
    assert txt.startswith("# [Sample](https://youtu.be/ABCDEFGHIJK)")
    assert "## Chapters" in txt and "[0:00]" in txt


def test_md_exporter_frontmatter(tmp_path: Path):
    doc = make_doc()
    path = MarkdownExporter(frontmatter=True).export(doc, tmp_path)
    txt = path.read_text(encoding="utf-8")
    assert txt.lstrip().startswith("---\n") and "title: Sample" in txt and "url: https://youtu.be/ABCDEFGHIJK" in txt


def test_md_exporter_optional_transcript(tmp_path: Path):
    doc = make_doc()
    path = MarkdownExporter(include_transcript=True).export(doc, tmp_path)
    txt = path.read_text(encoding="utf-8")
    assert "## Transcript" in txt and "[0:00] Hello world" in txt

