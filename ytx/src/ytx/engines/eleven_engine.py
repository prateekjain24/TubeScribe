from __future__ import annotations

from pathlib import Path
from typing import Callable
import os

from .base import TranscriptionEngine, EngineError
from .cloud_base import CloudEngineBase
from ..config import AppConfig
from ..models import TranscriptSegment


def _load_api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise EngineError(code="ENGINE", message="ELEVENLABS_API_KEY is not set in the environment")
    return key


class ElevenLabsEngine(CloudEngineBase, TranscriptionEngine):
    name = "elevenlabs"

    def transcribe(self, audio_path: Path, *, config: AppConfig, on_progress: Callable[[float], None] | None = None) -> list[TranscriptSegment]:
        # Placeholder: pending stable STT endpoint documentation variations.
        # For now, raise a clear error indicating implementation is pending.
        _ = _load_api_key()  # validate presence
        raise EngineError(code="ENGINE", message="ElevenLabs transcription not implemented yet")

