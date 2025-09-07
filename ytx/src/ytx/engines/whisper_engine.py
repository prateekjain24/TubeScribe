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
from typing import Any, Dict, Tuple

from .base import EngineError, TranscriptionEngine
from ..config import AppConfig
from ..models import TranscriptSegment
from . import register_engine

try:  # Import faster-whisper if available
    from faster_whisper import WhisperModel  # type: ignore
    _FW_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency surface
    WhisperModel = None  # type: ignore
    _FW_AVAILABLE = False


@register_engine
class WhisperEngine(TranscriptionEngine):
    name = "whisper"

    def __init__(self) -> None:  # light ctor; defer heavy work to methods
        if not _FW_AVAILABLE:
            # Do not raise here to allow help/registry to function without the dep.
            # Raise only when attempting to use the engine.
            pass

    # Simple in-process cache of loaded models keyed by (model, device, compute_type)
    _MODEL_CACHE: Dict[Tuple[str, str, str], Any] = {}

    def _ensure_available(self) -> None:
        if not _FW_AVAILABLE:
            raise EngineError(
                "faster-whisper is not installed. Install it via 'uv add faster-whisper'"
            )

    @staticmethod
    def _map_device(device: str) -> str:
        # faster-whisper/CTranslate2 accepts 'cpu', 'cuda', or 'auto'. Map 'metal' to 'cpu'.
        d = device.lower()
        if d in {"cpu", "cuda", "auto"}:
            return d
        if d == "metal":
            return "cpu"
        return "cpu"

    def _model_key(self, config: AppConfig) -> Tuple[str, str, str]:
        device = self._map_device(config.device)
        compute = str(config.compute_type)
        return (config.model, device, compute)

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

    def transcribe(self, audio_path: Path, *, config: AppConfig) -> list[TranscriptSegment]:
        self._ensure_available()
        # Ensure model loads (and is cached) early; actual transcription comes later.
        _ = self._get_model(config)
        # Implementation arrives in WHISPER-004..007
        raise EngineError("Whisper transcription not implemented yet (pending later tickets)")

    def detect_language(self, audio_path: Path, *, config: AppConfig) -> str | None:
        # Optional implementation in later tickets; return None by default.
        return None


__all__ = ["WhisperEngine"]
