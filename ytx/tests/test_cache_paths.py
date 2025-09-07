from pathlib import Path
from ytx.cache import build_artifact_paths, artifacts_exist


def test_build_artifact_paths_and_existence(tmp_path: Path):
    paths = build_artifact_paths(
        video_id="0jpcFxY_38k",
        engine="whisper",
        model="small",
        config_hash="deadbeef",
        root=tmp_path,
        create=True,
    )
    assert paths.dir.exists()
    assert not artifacts_exist(paths)
    (paths.transcript_json).write_text("{}", encoding="utf-8")
    assert not artifacts_exist(paths)
    (paths.captions_srt).write_text("1\n00:00:00,000 --> 00:00:00,500\nHi\n", encoding="utf-8")
    assert artifacts_exist(paths)

