from __future__ import annotations

"""Gemini engine skeleton using google-generativeai.

GEMINI-001..003 scope:
- Create module and import `google.generativeai as genai` (optional dep).
- Load API key from environment (GEMINI_API_KEY preferred; fallback GOOGLE_API_KEY).
- Configure the client and basic model setup via `GenerativeModel`.

Actual audio handling and transcription prompt will be implemented in later tickets.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .base import EngineError, TranscriptionEngine
from ..config import AppConfig
from ..models import TranscriptSegment
from . import register_engine

try:  # Optional dependency
    import google.generativeai as genai  # type: ignore
    _GENAI_AVAILABLE = True
except Exception:  # pragma: no cover - dependency not installed
    genai = None  # type: ignore
    _GENAI_AVAILABLE = False


def _load_api_key() -> str:
    """Load Gemini API key from environment.

    Prefers GEMINI_API_KEY, then GOOGLE_API_KEY. Performs a light format check.
    """
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise EngineError(
            "Gemini API key not found. Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your environment/.env"
        )
    # Light validation: common Google API keys start with 'AIza'
    if not key.startswith("AIza") or len(key) < 24:
        raise EngineError("Invalid Gemini API key format; please verify your GEMINI_API_KEY")
    return key


def _ensure_client_configured() -> None:
    if not _GENAI_AVAILABLE:
        raise EngineError(
            "google-generativeai is not installed. Install it via 'uv add google-generativeai'"
        )
    key = _load_api_key()
    try:
        genai.configure(api_key=key)  # type: ignore[attr-defined]
    except Exception as e:  # pragma: no cover - depends on library version
        raise EngineError(f"Failed to configure Gemini client: {e}") from e


def _resolve_model_name(model: str | None) -> str:
    # Default to a fast, recent model suited for transcription-style tasks later.
    default = "gemini-2.5-flash"
    if not model:
        return default
    m = model.strip()
    # If user passed a non-Gemini alias like 'small', ignore and use default.
    if not m.lower().startswith("gemini-"):
        return default
    return m


@register_engine
class GeminiEngine(TranscriptionEngine):
    name = "gemini"

    def __init__(self) -> None:
        # Defer hard failures until use; allow CLI to list engines even if dep missing.
        pass

    def _get_model(self, config: AppConfig):  # type: ignore[no-untyped-def]
        _ensure_client_configured()
        model_name = _resolve_model_name(getattr(config, "model", None))
        gen_cfg: dict[str, Any] = {
            "temperature": 0.2,
            # Keep defaults lightweight; tune in later tickets.
        }
        try:
            return genai.GenerativeModel(model_name, generation_config=gen_cfg)  # type: ignore[attr-defined]
        except Exception as e:  # pragma: no cover
            raise EngineError(f"Failed to initialize Gemini model '{model_name}': {e}") from e

    def transcribe(
        self,
        audio_path: Path,
        *,
        config: AppConfig,
        on_progress: Callable[[float], None] | None = None,
    ) -> list[TranscriptSegment]:
        # Placeholder: actual transcription logic lands in GEMINI-006.. etc.
        raise EngineError("Gemini transcription not implemented yet (pending GEMINI-006..015)")

    def detect_language(self, audio_path: Path, *, config: AppConfig) -> str | None:
        # Not yet implemented; may be inferred during transcription prompt later.
        return None


__all__ = ["GeminiEngine"]

