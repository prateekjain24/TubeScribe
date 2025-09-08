from pathlib import Path
import importlib


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


def test_gemini_chunked_offset_no_inplace(monkeypatch, tmp_path):
    wav = tmp_path / 'src.wav'
    _write_silence_wav(wav, seconds=2.0)

    from ytx.engines.gemini_engine import GeminiEngine
    from ytx.config import AppConfig

    eng = GeminiEngine()

    # Force deterministic chunk ranges: two 1s chunks back-to-back
    monkeypatch.setattr('ytx.engines.gemini_engine.compute_chunks', lambda total, window_seconds, overlap_seconds: [(0.0, 1.0), (1.0, 2.0)])

    # Avoid real file slicing; just copy the source to chunk path
    def fake_slice(src, dst, *, start, end):
        data = Path(src).read_bytes()
        Path(dst).write_bytes(data)
        return Path(dst)

    monkeypatch.setattr('ytx.engines.gemini_engine.slice_wav_segment', fake_slice)

    # Bypass client/model and upload; return a fake response with a segment where end == start
    monkeypatch.setattr(eng, '_get_model', lambda cfg: object())
    monkeypatch.setattr(eng, '_upload_audio', lambda p: object())

    class Resp:
        def __init__(self, text):
            self.text = text

    import json
    payload = json.dumps({
        "segments": [
            {"start": 0.0, "end": 0.0, "text": "Hi"},
            {"start": 0.0, "end": 0.1, "text": "there"},
        ]
    })
    monkeypatch.setattr(eng, '_generate_with_retries', lambda *a, **k: Resp(payload))

    cfg = AppConfig(engine='gemini', model='gemini-2.5-flash')

    segs = eng._transcribe_chunked(wav, config=cfg, on_progress=None, window_seconds=1.0, overlap_seconds=0.0)
    assert segs and all(s.end > s.start for s in segs)


def test_openai_chunked_offset_no_inplace(monkeypatch, tmp_path):
    wav = tmp_path / 'src.wav'
    _write_silence_wav(wav, seconds=2.0)

    from ytx.engines.openai_engine import OpenAIEngine
    from ytx.config import AppConfig

    eng = OpenAIEngine()
    # Force two chunks
    monkeypatch.setattr('ytx.engines.openai_engine.compute_chunks', lambda total, window_seconds, overlap_seconds: [(0.0, 1.0), (1.0, 2.0)])
    monkeypatch.setattr('ytx.engines.openai_engine.slice_wav_segment', lambda src, dst, *, start, end: Path(dst).write_bytes(Path(src).read_bytes()) or Path(dst))

    def fake_single(path, *, config, on_progress=None):
        # Return a minimal object with zero duration to trigger the offset guard
        import types
        return [types.SimpleNamespace(id=0, start=0.0, end=0.0, text='x', confidence=None)]

    monkeypatch.setattr(eng, '_transcribe_single', fake_single)
    # Use a valid engine literal to satisfy AppConfig; engine value isn't used here
    cfg = AppConfig(engine='whisper', model='whisper-1')
    segs = eng._transcribe_chunked(wav, config=cfg, on_progress=None, window_seconds=1.0, overlap_seconds=0.0)
    assert segs and all(s.end > s.start for s in segs)


def test_deepgram_chunked_offset_no_inplace(monkeypatch, tmp_path):
    wav = tmp_path / 'src.wav'
    _write_silence_wav(wav, seconds=2.0)

    from ytx.engines.deepgram_engine import DeepgramEngine
    from ytx.config import AppConfig

    eng = DeepgramEngine()
    monkeypatch.setattr('ytx.engines.deepgram_engine.compute_chunks', lambda total, window_seconds, overlap_seconds: [(0.0, 1.0), (1.0, 2.0)])
    monkeypatch.setattr('ytx.engines.deepgram_engine.slice_wav_segment', lambda src, dst, *, start, end: Path(dst).write_bytes(Path(src).read_bytes()) or Path(dst))

    def fake_single(path, *, config, on_progress=None):
        import types
        return [types.SimpleNamespace(id=0, start=0.0, end=0.0, text='x', confidence=None)]

    monkeypatch.setattr(eng, '_transcribe_single', fake_single)
    cfg = AppConfig(engine='whisper', model='nova-2')
    segs = eng._transcribe_chunked(wav, config=cfg, on_progress=None, window_seconds=1.0, overlap_seconds=0.0)
    assert segs and all(s.end > s.start for s in segs)
