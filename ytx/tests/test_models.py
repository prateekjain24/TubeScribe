from ytx.models import TranscriptSegment, TranscriptDoc, Chapter, Summary


def test_transcript_segment_validation():
    s = TranscriptSegment(id=0, start=0.0, end=1.0, text="hello")
    assert s.duration == 1.0

    try:
        TranscriptSegment(id=1, start=1.0, end=1.0, text="bad")
    except Exception:
        pass
    else:
        raise AssertionError("expected validation error for end <= start")


def test_transcript_doc_serialization_roundtrip():
    segs = [TranscriptSegment(id=0, start=0.0, end=0.5, text="hi")]
    doc = TranscriptDoc(
        video_id="abc123def45",
        source_url="https://youtu.be/abc123def45",
        title="t",
        duration=0.5,
        language="en",
        engine="whisper",
        model="small",
        segments=segs,
        chapters=[Chapter(title="Intro", start=0.0, end=0.5)],
        summary=Summary(tldr="tl;dr", bullets=["a", "b"]),
    )
    js = doc.model_dump_json()
    assert "segments" in js and "video_id" in js
    back = TranscriptDoc.model_validate_json(js)
    assert back.video_id == doc.video_id

