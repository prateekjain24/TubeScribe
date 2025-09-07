from __future__ import annotations

"""Gemini engine skeleton using google-generativeai.

GEMINI-001..003 scope:
- Create module and import `google.generativeai as genai` (optional dep).
- Load API key from environment (GEMINI_API_KEY preferred; fallback GOOGLE_API_KEY).
- Configure the client and basic model setup via `GenerativeModel`.

Actual audio handling and transcription prompt will be implemented in later tickets.
"""

import os
from pathlib import Path
from typing import Any, Callable
import mimetypes
from ..audio import probe_duration

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

    def _guess_mime(self, path: Path) -> str | None:
        mt, _ = mimetypes.guess_type(str(path))
        return mt

    def _upload_audio(self, path: Path):  # type: ignore[no-untyped-def]
        """Upload audio via Files API and return file handle/reference.

        Performs basic size checks and infers MIME type from filename when possible.
        """
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise EngineError(f"audio file does not exist: {p}")
        size = p.stat().st_size
        # Hard limit safeguard; official limits depend on account/features. Keep conservative.
        two_gb = 2 * 1024 * 1024 * 1024
        if size > two_gb:
            raise EngineError("audio file is larger than 2GB; exceeds common Files API limits")
        mime = self._guess_mime(p) or "audio/wav"
        try:
            # google-generativeai accepts path as 'path=' or file object; include display_name where supported.
            file = genai.upload_file(path=str(p), mime_type=mime)  # type: ignore[attr-defined]
        except Exception as e:  # pragma: no cover
            raise EngineError(f"Gemini file upload failed: {e}") from e
        # Expect object with .uri, .name, .mime_type
        return file

    def _build_prompt(self, *, language: str | None) -> str:
        # Ask for strict JSON with segments and second-based timestamps.
        lang_clause = f"in {language} " if language else ""
        return (
            "You are a transcription engine. "
            f"Transcribe the audio verbatim {lang_clause}and return STRICT JSON only, "
            "with no prose. Use this schema: "
            "{\n  \"language\": string (ISO 639-1, optional),\n  \"segments\": [\n    { \"start\": number (seconds, >=0), \"end\": number (>start), \"text\": string }\n  ]\n}. "
            "Ensure timestamps are in seconds with decimals, monotonic and non-overlapping."
        )

    def transcribe(
        self,
        audio_path: Path,
        *,
        config: AppConfig,
        on_progress: Callable[[float], None] | None = None,
    ) -> list[TranscriptSegment]:
        model = self._get_model(config)
        # Upload audio first
        file = self._upload_audio(Path(audio_path))
        prompt = self._build_prompt(language=config.language)
        if on_progress:
            try:
                on_progress(0.05)
            except Exception:
                pass
        try:
            # Content order: file then instruction text
            resp = model.generate_content([file, prompt], request_options={"timeout": 600})  # type: ignore[attr-defined]
        except Exception as e:  # pragma: no cover
            raise EngineError(f"Gemini generate_content failed: {e}") from e
        # Try to parse strict JSON per prompt
        payload_text = None
        try:
            payload_text = getattr(resp, "text", None)
            if not payload_text:
                cands = getattr(resp, "candidates", None)
                if cands and len(cands) and getattr(cands[0], "content", None):
                    parts = getattr(cands[0].content, "parts", None)
                    if parts:
                        payload_text = "".join(getattr(p, "text", "") for p in parts if getattr(p, "text", ""))
        except Exception:
            payload_text = None
        try:
            import orjson as _orjson  # type: ignore

            data = _orjson.loads((payload_text or "").encode("utf-8")) if payload_text else None
        except Exception:
            import json as _json

            data = None
            if payload_text:
                try:
                    data = _json.loads(payload_text)
                except Exception:
                    data = None
        # Calculate duration for fallback bounds
        try:
            dur = probe_duration(audio_path)
        except Exception:
            dur = 0.0
        segments: list[TranscriptSegment] = []
        if isinstance(data, dict) and isinstance(data.get("segments"), list):
            prev_end = 0.0
            for i, seg in enumerate(data["segments"]):
                try:
                    txt = str(seg.get("text") or "").strip()
                    if not txt:
                        continue
                    start = float(seg.get("start") if seg.get("start") is not None else prev_end)
                    end = float(seg.get("end") if seg.get("end") is not None else start)
                    if start < prev_end:
                        start = prev_end
                    if end <= start:
                        end = start + 0.001
                    prev_end = end
                    segments.append(TranscriptSegment(id=len(segments), start=start, end=end, text=txt))
                except Exception:
                    continue
        if not segments:
            # Fallback: treat entire response text as one segment if any text present
            text_fallback = (payload_text or "").strip()
            if not text_fallback:
                raise EngineError("Gemini returned no usable content for transcription")
            segments = [TranscriptSegment(id=0, start=0.0, end=max(0.001, float(dur)), text=text_fallback)]
        if on_progress:
            try:
                on_progress(1.0)
            except Exception:
                pass
        return segments

    def detect_language(self, audio_path: Path, *, config: AppConfig) -> str | None:
        # Not yet implemented; may be inferred during transcription prompt later.
        return None


__all__ = ["GeminiEngine"]
