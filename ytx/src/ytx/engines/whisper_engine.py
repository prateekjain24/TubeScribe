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
from typing import Any

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

    def _ensure_available(self) -> None:
        if not _FW_AVAILABLE:
            raise EngineError(
                "faster-whisper is not installed. Install it via 'uv add faster-whisper'"
            )

    def transcribe(self, audio_path: Path, *, config: AppConfig) -> list[TranscriptSegment]:
        self._ensure_available()
        # Implementation arrives in WHISPER-004..007
        raise EngineError("Whisper transcription not implemented yet (pending later tickets)")

    def detect_language(self, audio_path: Path, *, config: AppConfig) -> str | None:
        # Optional implementation in later tickets; return None by default.
        return None


__all__ = ["WhisperEngine"]

