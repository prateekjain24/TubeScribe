import time
from pathlib import Path


def test_compute_chunks_perf():
    from ytx.chunking import compute_chunks

    start = time.perf_counter()
    chunks = compute_chunks(2 * 3600.0, window_seconds=600.0, overlap_seconds=2.0)  # 2 hours
    dur = time.perf_counter() - start
    # Expect ~12 chunks; ensure this computation is effectively instantaneous
    assert len(chunks) >= 10
    assert dur < 0.01


def test_export_srt_perf(tmp_path: Path):
    from ytx.exporters.srt_exporter import SRTExporter
    from ytx.models import TranscriptDoc, TranscriptSegment

    segs = [
        TranscriptSegment(id=i, start=i * 0.5, end=i * 0.5 + 0.49, text=f"Line {i} of text")
        for i in range(300)
    ]
    doc = TranscriptDoc(
        video_id="perfvid",
        source_url="https://youtu.be/perfvid",
        title="Perf",
        duration=float(segs[-1].end),
        language="en",
        engine="whisper",
        model="small",
        segments=segs,
    )
    start = time.perf_counter()
    path = SRTExporter().export(doc, tmp_path)
    dur = time.perf_counter() - start
    assert path.exists() and path.stat().st_size > 1000
    # Generous bound to avoid flakiness
    assert dur < 0.5

