from pathlib import Path
from datetime import datetime, timezone

from ytx.cache import scan_cache, build_artifact_paths, write_meta, build_meta_payload
from ytx.config import AppConfig
from ytx.models import VideoMetadata


def test_scan_cache_reads_correct_video_id(tmp_path: Path):
    # Arrange: create canonical files under <root>/<vid>/<engine>/<model>/<hash>/
    vid = "TLSSVT1GI2Y"
    cfg = AppConfig(engine="whisper", model="small")
    paths = build_artifact_paths(video_id=vid, engine=cfg.engine, model=cfg.model, config_hash="deadbeef", root=tmp_path, create=True)
    # Create minimal artifacts
    (paths.transcript_json).write_text("{}", encoding="utf-8")
    (paths.captions_srt).write_text("1\n00:00:00,000 --> 00:00:00,500\nHi\n", encoding="utf-8")
    vm = VideoMetadata(id=vid, title="t", duration=1.0, url=f"https://youtu.be/{vid}")
    write_meta(paths, build_meta_payload(video_id=vid, config=cfg, source=vm, provider=cfg.engine))

    # Act
    entries = scan_cache(root=tmp_path)

    # Assert
    assert any(e.video_id == vid for e in entries)

