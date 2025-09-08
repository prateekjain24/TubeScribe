from pathlib import Path
from datetime import datetime, timezone
from typer.testing import CliRunner


def _write_doc_files(root: Path, video_id: str = "CACHEID12345") -> Path:
    # Build a fake cache layout: <root>/<video_id>/<engine>/<model>/<hash>/transcript.json
    base = root / video_id / "whisper" / "small" / "deadbeef"
    base.mkdir(parents=True, exist_ok=True)
    from ytx.models import TranscriptDoc, TranscriptSegment
    doc = TranscriptDoc(
        video_id=video_id,
        source_url=f"https://youtu.be/{video_id}",
        title="Cache Title",
        duration=10.0,
        language="en",
        engine="whisper",
        model="small",
        segments=[TranscriptSegment(id=0, start=0.0, end=0.5, text="Hi")],
    )
    (base / "transcript.json").write_text(doc.model_dump_json(), encoding="utf-8")
    return base


def test_cli_export_from_cache(monkeypatch, tmp_path: Path):
    # Prepare fake cache entry
    cache_root = tmp_path / "cache"
    entry_dir = _write_doc_files(cache_root)

    # Monkeypatch scan_cache to return a single entry pointing at our fake dir
    from ytx.cache import CacheEntry

    def fake_scan_cache(root=None):
        return [
            CacheEntry(
                dir=entry_dir,
                video_id="CACHEID12345",
                engine="whisper",
                model="small",
                config_hash="deadbeef",
                created_at=datetime.now(timezone.utc),
                size_bytes=123,
                title="Cache Title",
                url=f"https://youtu.be/CACHEID12345",
            )
        ]

    import importlib
    cli = importlib.import_module('ytx.cli')
    import ytx.cache as cache_mod
    monkeypatch.setattr(cache_mod, 'scan_cache', fake_scan_cache)

    outdir = tmp_path / "notes"
    outdir.mkdir()
    runner = CliRunner()
    res = runner.invoke(
        cli.app,
        [
            "export",
            "--video-id",
            "CACHEID12345",
            "--to",
            "md",
            "--output-dir",
            str(outdir),
        ],
    )
    assert res.exit_code == 0, res.output
    md = outdir / "CACHEID12345.md"
    assert md.exists() and "Cache Title" in md.read_text(encoding="utf-8")
