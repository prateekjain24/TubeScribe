from __future__ import annotations

"""whisper.cpp engine with Metal support (via -ml / -ngl).

Requires a gguf/ggml model file path. Provide via:
- AppConfig.model (path to .gguf/.bin), or
- env `YTX_WHISPERCPP_MODEL_PATH`

Binary resolution (in order):
- `AppConfig.whispercpp_bin` if it's an existing path
- name in PATH (default: `main`)
- env `YTX_WHISPERCPP_BIN`
"""

from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
from typing import Any, Callable

from .base import EngineError, TranscriptionEngine
from ..config import AppConfig
from ..models import TranscriptSegment
from . import register_engine


@register_engine
class WhisperCppEngine(TranscriptionEngine):
    name = "whispercpp"

    def _resolve_bin(self, cfg: AppConfig) -> str:
        # Prefer explicit path
        c = cfg.whispercpp_bin
        env_bin = os.getenv("YTX_WHISPERCPP_BIN")
        for candidate in [c, env_bin, "main"]:
            if not candidate:
                continue
            p = Path(candidate)
            if p.exists() and p.is_file():
                return str(p)
            found = shutil.which(candidate)
            if found:
                return found
        raise EngineError("whisper.cpp binary not found. Set YTX_WHISPERCPP_BIN or whispercpp_bin")

    def _resolve_model(self, cfg: AppConfig) -> Path:
        # Accept path-like model only
        env_model = os.getenv("YTX_WHISPERCPP_MODEL_PATH")
        for m in [cfg.model, env_model]:
            if not m:
                continue
            p = Path(os.path.expanduser(m))
            if p.exists() and p.is_file() and p.suffix.lower() in {".gguf", ".bin"}:
                return p
        raise EngineError(
            "whisper.cpp requires a local gguf/ggml model file. "
            "Provide a path in AppConfig.model or set YTX_WHISPERCPP_MODEL_PATH"
        )

    def transcribe(
        self,
        audio_path: Path,
        *,
        config: AppConfig,
        on_progress: Callable[[float], None] | None = None,
    ) -> list[TranscriptSegment]:
        bin_path = self._resolve_bin(config)
        model_path = self._resolve_model(config)
        threads = config.whispercpp_threads or os.cpu_count() or 4
        ngl = max(0, int(config.whispercpp_ngl))

        with tempfile.TemporaryDirectory() as td:
            prefix = Path(td) / "out"
            cmd = [
                bin_path,
                "-ml",
                "-ngl",
                str(ngl),
                "-t",
                str(threads),
                "-m",
                str(model_path),
                "-f",
                str(audio_path),
                "-oj",
                "-of",
                str(prefix),
            ]
            try:
                proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
            except Exception as e:
                raise EngineError(f"whisper.cpp execution failed: {e}")
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip().splitlines()[-10:]
                raise EngineError("whisper.cpp failed: " + " | ".join(err))
            json_path = prefix.with_suffix(".json")
            if not json_path.exists():
                raise EngineError("whisper.cpp did not produce JSON output (-oj)")
            try:
                data = json.loads(json_path.read_text())
            except Exception as e:
                raise EngineError(f"invalid JSON output: {e}")

        segments = self._parse_segments(data)
        # Progress callback not wired (whisper.cpp does not expose easy progress); set to done
        if on_progress:
            try:
                on_progress(1.0)
            except Exception:
                pass
        return segments

    def _parse_segments(self, data: Any) -> list[TranscriptSegment]:
        # Try to locate segments array in common whisper.cpp JSON structures
        segs = None
        if isinstance(data, dict):
            if isinstance(data.get("segments"), list):
                segs = data["segments"]
            elif isinstance(data.get("transcription"), dict) and isinstance(
                data["transcription"].get("segments"), list
            ):
                segs = data["transcription"]["segments"]
        if segs is None:
            raise EngineError("missing segments in whisper.cpp JSON output")
        out: list[TranscriptSegment] = []
        prev = 0.0
        for i, s in enumerate(segs):
            try:
                start = float(s.get("start", 0.0))
                end = float(s.get("end", start))
                text = str(s.get("text", "")).strip()
            except Exception:
                continue
            if not text:
                continue
            if start < prev:
                start = prev
            if end <= start:
                end = start + 0.001
            prev = end
            out.append(TranscriptSegment(id=i, start=start, end=end, text=text, confidence=None))
        return out

    def detect_language(self, audio_path: Path, *, config: AppConfig) -> str | None:
        # Not implemented for whisper.cpp path; could parse JSON "language" if present
        return None


__all__ = ["WhisperCppEngine"]

