from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..config import AppConfig
from ..models import TranscriptSegment


class EngineError(RuntimeError):
    """Raised by engines on unrecoverable errors."""


@runtime_checkable
class TranscriptionEngine(Protocol):
    """Protocol for transcription engines.

    Engines consume a normalized audio file (e.g., 16 kHz mono WAV) and return
    a list of transcript segments for the entire file.
    """

    # Unique engine name (e.g., "whisper", "gemini")
    name: str

    def transcribe(self, audio_path: Path, *, config: AppConfig) -> list[TranscriptSegment]:
        """Transcribe the audio file and return transcript segments.

        - `audio_path` should point to a local file accessible to the engine.
        - `config` contains engine/model/language/device preferences.
        """
        ...

    def detect_language(self, audio_path: Path, *, config: AppConfig) -> str | None:
        """Optionally detect the primary spoken language, if supported.

        Default behavior for engines that do not support detection may be to
        return `None`.
        """
        ...


__all__ = ["EngineError", "TranscriptionEngine"]

