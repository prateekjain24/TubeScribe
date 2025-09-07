from pathlib import Path
from ytx.exporters.json_exporter import JSONExporter
from ytx.exporters.srt_exporter import SRTExporter
from ytx.models import TranscriptDoc, TranscriptSegment


def make_doc():
    return TranscriptDoc(
        video_id="v1234567890",
        source_url="https://youtu.be/v1234567890",
        title="title",
        duration=1.0,
        language="en",
        engine="whisper",
        model="small",
        segments=[
            TranscriptSegment(id=0, start=0.0, end=0.5, text="Hello world"),
            TranscriptSegment(id=1, start=0.5, end=1.0, text="Testing"),
        ],
    )


def test_json_exporter_roundtrip(tmp_path: Path):
    doc = make_doc()
    path = JSONExporter().export(doc, tmp_path)
    assert path.exists()
    data = path.read_text(encoding="utf-8")
    assert '"video_id"' in data


def test_srt_exporter_creates_file(tmp_path: Path):
    doc = make_doc()
    path = SRTExporter().export(doc, tmp_path)
    assert path.exists()
    txt = path.read_text(encoding="utf-8")
    assert "-->" in txt and "Hello" in txt

