from pathlib import Path

from ytx.exporters.markdown_exporter import MarkdownExporter
from ytx.models import TranscriptDoc, TranscriptSegment


def make_doc_no_chapters() -> TranscriptDoc:
    segs = [TranscriptSegment(id=0, start=0.0, end=300.0, text="...")]
    return TranscriptDoc(
        video_id="VIDAUTOCHAP",
        source_url="https://youtu.be/VIDAUTOCHAP",
        title="AutoChapters",
        duration=601.0,  # just over 10 minutes
        language="en",
        engine="whisper",
        model="small",
        segments=segs,
        chapters=None,
        summary=None,
    )


def test_auto_chapters_render(tmp_path: Path):
    doc = make_doc_no_chapters()
    path = MarkdownExporter(auto_chapter_every_sec=300.0).export(doc, tmp_path)  # 5 minutes
    txt = path.read_text(encoding="utf-8")
    # Expect a Chapters section with [0:00] and [5:00]
    assert "## Chapters" in txt
    assert "[0:00]" in txt and "[5:00]" in txt

