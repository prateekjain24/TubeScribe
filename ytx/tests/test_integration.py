from pathlib import Path
from typer.testing import CliRunner
import importlib
import json


def _write_silence_wav(path: Path, seconds: float = 1.0, rate: int = 16000):
    import wave, struct

    nframes = int(seconds * rate)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        silence = struct.pack('<h', 0)
        for _ in range(nframes):
            w.writeframesraw(silence)


def test_integration_transcribe_minimal(tmp_path, monkeypatch):
    # Configure cache to tmp
    monkeypatch.setenv('YTX_CACHE_DIR', str(tmp_path))

    # Import CLI after patching dependencies in its module
    cli = importlib.import_module('ytx.cli')

    # Patch metadata fetch to avoid yt-dlp
    from ytx.models import VideoMetadata

    def fake_meta(url: str, **kwargs):
        return VideoMetadata(id="ABCDEFGHIJK", title="Test", duration=1.0, url=url)

    monkeypatch.setattr(cli, 'fetch_metadata', fake_meta)

    # Prepare a tiny WAV and patch download/normalize
    wav_src = tmp_path / 'src.wav'
    _write_silence_wav(wav_src, seconds=1.0)

    def fake_download(meta, out_dir, **kwargs):
        return wav_src

    def fake_normalize(src, dst, **kwargs):
        # For test, just copy
        data = Path(src).read_bytes()
        Path(dst).write_bytes(data)
        return Path(dst)

    monkeypatch.setattr(cli, 'download_audio', fake_download)
    monkeypatch.setattr(cli, 'normalize_wav', fake_normalize)

    # Patch engine to return deterministic segments
    class DummyEngine:
        def transcribe(self, audio_path, *, config, on_progress=None):
            return [
                importlib.import_module('ytx.models').TranscriptSegment(id=0, start=0.0, end=0.5, text='Hello'),
                importlib.import_module('ytx.models').TranscriptSegment(id=1, start=0.5, end=1.0, text='World'),
            ]

        def detect_language(self, audio_path, *, config):
            return 'en'

    monkeypatch.setattr(cli, 'WhisperEngine', lambda: DummyEngine())

    runner = CliRunner()
    url = 'https://youtu.be/ABCDEFGHIJK'
    res = runner.invoke(cli.app, ['transcribe', url, '--engine', 'whisper', '--timestamps', 'native'])
    assert res.exit_code == 0

    # Verify artifacts exist in cache dir
    json_files = list(tmp_path.rglob('ABCDEFGHIJK.json'))
    srt_files = list(tmp_path.rglob('ABCDEFGHIJK.srt'))
    assert json_files and srt_files
    payload = json.loads(json_files[0].read_text(encoding='utf-8'))
    assert payload.get('video_id') == 'ABCDEFGHIJK'
    assert len(payload.get('segments', [])) == 2

