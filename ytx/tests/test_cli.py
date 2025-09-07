from typer.testing import CliRunner
import sys, types, importlib


def test_cli_version_and_hello(monkeypatch):
    # Stub heavy whisper import before importing CLI
    mod = types.ModuleType('ytx.engines.whisper_engine')
    class DummyWhisper:  # minimal stub
        pass
    mod.WhisperEngine = DummyWhisper
    monkeypatch.setitem(sys.modules, 'ytx.engines.whisper_engine', mod)
    cli = importlib.import_module('ytx.cli')
    runner = CliRunner()
    res = runner.invoke(cli.app, ["--version"])  # global version flag
    assert res.exit_code == 0
    assert "ytx" in res.output
    # Basic hello command should exist and accept a name
    res2 = runner.invoke(cli.app, ["hello", "--name", "test"])
    assert res2.exit_code == 0 and "Hello, test" in res2.output


def test_cli_health_monkeypatched(monkeypatch):
    mod = types.ModuleType('ytx.engines.whisper_engine')
    class DummyWhisper: pass
    mod.WhisperEngine = DummyWhisper
    monkeypatch.setitem(sys.modules, 'ytx.engines.whisper_engine', mod)
    cli = importlib.import_module('ytx.cli')
    # Patch ensure_ffmpeg to avoid system dependency
    monkeypatch.setattr(cli, "ensure_ffmpeg", lambda: None, raising=False)

    class FakeResp:
        def __init__(self, status_code=200):
            self.status_code = status_code

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, *a, **k):
            return FakeResp(200)

    import httpx

    monkeypatch.setattr(httpx, "Client", FakeClient)
    runner = CliRunner()
    res = runner.invoke(cli.app, ["health"])
    assert res.exit_code == 0
    assert "ytx health" in res.output


def test_cli_transcribe_rejects_bad_url(monkeypatch):
    mod = types.ModuleType('ytx.engines.whisper_engine')
    class DummyWhisper: pass
    mod.WhisperEngine = DummyWhisper
    monkeypatch.setitem(sys.modules, 'ytx.engines.whisper_engine', mod)
    cli = importlib.import_module('ytx.cli')
    runner = CliRunner()
    res = runner.invoke(cli.app, ["transcribe", "not-a-url"])
    # Typer treats bad parameter as exit code 2
    assert res.exit_code != 0
