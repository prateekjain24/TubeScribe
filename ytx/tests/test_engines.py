from pathlib import Path
import types
import pytest


def test_whisper_engine_transcribe_mock(monkeypatch):
    # Stub faster_whisper before importing engine to avoid heavy deps
    import sys, types as _types
    fw = _types.ModuleType('faster_whisper')
    class DummyWM: pass
    fw.WhisperModel = DummyWM
    sys.modules['faster_whisper'] = fw
    from ytx.engines.whisper_engine import WhisperEngine
    from ytx.config import AppConfig
    import ytx.engines.whisper_engine as we

    class FakeSeg:
        def __init__(self, start, end, text, avg_logprob=-0.1):
            self.start = start
            self.end = end
            self.text = text
            self.avg_logprob = avg_logprob

    def fake_model_transcribe(*args, **kwargs):
        segs = [FakeSeg(0.0, 0.5, "Hello"), FakeSeg(0.5, 1.0, "World")]
        info = types.SimpleNamespace(language="en")
        return iter(segs), info

    fake_model = types.SimpleNamespace(transcribe=fake_model_transcribe)
    eng = WhisperEngine()
    monkeypatch.setattr(eng, "_get_model", lambda cfg: fake_model)
    monkeypatch.setattr(we, "probe_duration", lambda p: 1.0)
    segs = eng.transcribe(Path("dummy.wav"), config=AppConfig(engine="whisper", model="small"))
    assert [s.text for s in segs] == ["Hello", "World"]


def test_gemini_engine_transcribe_mock(monkeypatch):
    from ytx.engines.gemini_engine import GeminiEngine
    from ytx.config import AppConfig
    import ytx.engines.gemini_engine as ge

    eng = GeminiEngine()

    # Bypass client/model setup and upload
    monkeypatch.setattr(eng, "_get_model", lambda cfg: object())
    monkeypatch.setattr(eng, "_upload_audio", lambda p: object())
    # Fake API response with JSON segments
    class Resp:
        def __init__(self, text):
            self.text = text

    payload = {
        "segments": [
            {"start": 0.0, "end": 0.5, "text": "Hi"},
            {"start": 0.5, "end": 1.0, "text": "there"},
        ]
    }
    import json

    monkeypatch.setattr(eng, "_generate_with_retries", lambda *a, **k: Resp(json.dumps(payload)))
    monkeypatch.setattr(ge, "probe_duration", lambda p: 1.0)
    cfg = AppConfig(engine="gemini", model="gemini-2.5-flash")
    segs = eng.transcribe(Path("dummy.wav"), config=cfg)
    assert [s.text for s in segs] == ["Hi", "there"]
