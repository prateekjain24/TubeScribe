from __future__ import annotations

"""Whisper engine (faster-whisper) skeleton.

Grounded in faster-whisper API:
- Import: `from faster_whisper import WhisperModel`
- Construct: `WhisperModel(model_size_or_path, device=..., compute_type=...)`
- Transcribe: `segments, info = model.transcribe(audio_path, ...)`

This ticket (WHISPER-003) sets up the module and handles import errors
gracefully. Actual model loading and transcription will be implemented in
subsequent tickets.
"""

from pathlib import Path
from typing import Any, Dict, Tuple, Callable

from .base import EngineError, TranscriptionEngine
from ..config import AppConfig
from ..models import TranscriptSegment
from . import register_engine
from ..audio import probe_duration

_FW_AVAILABLE = None  # lazy import status


@register_engine
class WhisperEngine(TranscriptionEngine):
    name = "whisper"

    def __init__(self) -> None:  # light ctor; defer heavy work to methods
        # Lazy import; no heavy work on construction
        pass

    # Simple in-process cache of loaded models keyed by (model, device, compute_type)
    _MODEL_CACHE: Dict[Tuple[str, str, str], Any] = {}

    def _ensure_available(self) -> None:
        global _FW_AVAILABLE
        if _FW_AVAILABLE is None:
            try:
                from faster_whisper import WhisperModel as _WM  # type: ignore
                globals()['WhisperModel'] = _WM  # type: ignore
                _FW_AVAILABLE = True
            except Exception:  # pragma: no cover
                _FW_AVAILABLE = False
        if not _FW_AVAILABLE:
            raise EngineError(code="ENGINE", message="faster-whisper is not installed. Install it via 'pip install faster-whisper'")

    @staticmethod
    def _map_device(device: str) -> str:
        # faster-whisper/CTranslate2 accepts 'cpu', 'cuda', or 'auto'. Map 'metal' to 'cpu'.
        d = device.lower()
        if d in {"cpu", "cuda", "auto"}:
            return d
        if d == "metal":
            return "cpu"
        return "cpu"

    def _resolve_compute_type(self, config: AppConfig) -> str:
        ct = str(config.compute_type)
        if ct == "auto":
            d = self._map_device(config.device)
            return "float16" if d == "cuda" else "int8"
        return ct

    def _validate_model_name(self, model: str) -> str:
        name = model.strip()
        # Allow local or remote paths
        if "/" in name or name.startswith(".") or name.startswith("~"):
            return name
        allowed = {
            "tiny",
            "tiny.en",
            "base",
            "base.en",
            "small",
            "small.en",
            "medium",
            "medium.en",
            "large-v1",
            "large-v2",
            "large-v3",
            "large-v3-turbo",
        }
        if name in allowed:
            return name
        raise EngineError(
            "Unknown Whisper model name. Supported: "
            + ", ".join(sorted(allowed))
            + "; or provide a local/remote model path"
        )

    def _model_key(self, config: AppConfig) -> Tuple[str, str, str]:
        device = self._map_device(config.device)
        compute = self._resolve_compute_type(config)
        model_name = self._validate_model_name(config.model)
        return (model_name, device, compute)

    def _get_model(self, config: AppConfig) -> Any:
        self._ensure_available()
        key = self._model_key(config)
        if key in self._MODEL_CACHE:
            return self._MODEL_CACHE[key]
        model_name, device, compute_type = key
        try:
            model = WhisperModel(model_name, device=device, compute_type=compute_type)  # type: ignore[name-defined]
        except Exception as e:  # pragma: no cover - depends on local env/network
            raise EngineError(
                f"Failed to load Whisper model '{model_name}' on {device} ({compute_type}): {e}"
            ) from e
        self._MODEL_CACHE[key] = model
        return model

    def transcribe(
        self,
        audio_path: Path,
        *,
        config: AppConfig,
        on_progress: Callable[[float], None] | None = None,
    ) -> list[TranscriptSegment]:
        self._ensure_available()
        model = self._get_model(config)
        total_dur = None
        try:
            total_dur = probe_duration(audio_path)
        except Exception:
            total_dur = None
        try:
            try:
                segments_iter, info = model.transcribe(
                    str(audio_path),
                    language=config.language,
                    vad_filter=True,
                    beam_size=5,
                    batch_size=8,
                    word_timestamps=False,
                )
            except TypeError:
                # Older faster-whisper versions may not support batch_size
                segments_iter, info = model.transcribe(
                    str(audio_path),
                    language=config.language,
                    vad_filter=True,
                    beam_size=5,
                    word_timestamps=False,
                )
        except Exception as e:  # pragma: no cover
            raise EngineError(f"Whisper transcription failed: {e}") from e

        results: list[TranscriptSegment] = []
        prev_end = 0.0
        for i, s in enumerate(segments_iter):
            try:
                start = float(getattr(s, "start", 0.0) or 0.0)
                end = float(getattr(s, "end", start))
                text = str(getattr(s, "text", "")).strip()
                conf = getattr(s, "avg_logprob", None)
            except Exception:
                continue
            if not text:
                continue
            # Enforce monotonic boundaries
            if start < prev_end:
                start = prev_end
            if end <= start:
                end = start + 0.001
            prev_end = end
            if on_progress and total_dur and total_dur > 0:
                ratio = max(0.0, min(1.0, end / total_dur))
                try:
                    on_progress(ratio)
                except Exception:
                    pass
            results.append(TranscriptSegment(id=i, start=start, end=end, text=text, confidence=conf))
        if on_progress:
            try:
                on_progress(1.0)
            except Exception:
                pass
        return results

    def detect_language(self, audio_path: Path, *, config: AppConfig) -> str | None:
        self._ensure_available()
        model = self._get_model(config)
        try:
            try:
                _, info = model.transcribe(
                    str(audio_path),
                    language=None,  # auto-detect
                    vad_filter=True,
                    beam_size=1,
                    batch_size=8,
                    word_timestamps=False,
                )
            except TypeError:
                _, info = model.transcribe(
                    str(audio_path),
                    language=None,
                    vad_filter=True,
                    beam_size=1,
                    word_timestamps=False,
                )
            return getattr(info, "language", None)
        except Exception:
            return None


__all__ = ["WhisperEngine"]
