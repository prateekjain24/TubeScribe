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
from ..chunking import compute_chunks, slice_wav_segment
from ..stitch import stitch_segments
import tempfile
from tenacity import Retrying, stop_after_attempt, wait_random_exponential, retry_if_exception

from .base import EngineError, TranscriptionEngine
from .cloud_base import CloudEngineBase
from ..config import AppConfig
from ..models import TranscriptSegment
from . import register_engine

_GENAI_AVAILABLE = None  # lazy import


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
    global _GENAI_AVAILABLE, genai
    if _GENAI_AVAILABLE is None:
        try:
            import google.generativeai as genai  # type: ignore
            globals()['genai'] = genai  # type: ignore
            _GENAI_AVAILABLE = True
        except Exception:
            _GENAI_AVAILABLE = False
    if not _GENAI_AVAILABLE:
        raise EngineError(code="ENGINE", message="google-generativeai is not installed. Install it via 'pip install google-generativeai'")
    key = _load_api_key()
    try:
        genai.configure(api_key=key)  # type: ignore[attr-defined]
    except Exception as e:  # pragma: no cover - depends on library version
        raise EngineError(code="ENGINE", message=f"Failed to configure Gemini client: {e}", cause=e)


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
class GeminiEngine(CloudEngineBase, TranscriptionEngine):
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
        # Decide chunking by policy or duration threshold
        try:
            duration = probe_duration(audio_path)
        except Exception:
            duration = 0.0
        window = 600.0  # 10 minutes
        overlap = 2.0
        if config.timestamp_policy == "chunked" or duration > window:
            return self._transcribe_chunked(audio_path, config=config, on_progress=on_progress, window_seconds=window, overlap_seconds=overlap)
        segs = self._transcribe_single(audio_path, config=config, on_progress=on_progress)
        if config.timestamp_policy == "none":
            # Collapse to a single text block
            text = " ".join(s.text for s in segs if s.text).strip()
            end = max((s.end for s in segs), default=duration)
            return [TranscriptSegment(id=0, start=0.0, end=max(0.001, float(end)), text=text)]
        return segs

    def _transcribe_single(
        self,
        audio_path: Path,
        *,
        config: AppConfig,
        on_progress: Callable[[float], None] | None = None,
    ) -> list[TranscriptSegment]:
        model = self._get_model(config)
        file = self._upload_audio(Path(audio_path))
        prompt = self._build_prompt(language=config.language)
        if on_progress:
            try:
                on_progress(0.05)
            except Exception:
                pass
        resp = self._generate_with_retries(model, [file, prompt], timeout=getattr(config, 'transcribe_timeout', 600))
        payload_text = self._extract_text_from_response(resp)
        data = self._loads_json_loose(self._strip_code_fences(payload_text or "")) if payload_text else None
        try:
            dur = probe_duration(audio_path)
        except Exception:
            dur = 0.0
        segments = self._parse_segments_from_data_or_text(data, payload_text, total_duration=dur)
        if on_progress:
            try:
                on_progress(1.0)
            except Exception:
                pass
        return segments

    def _transcribe_chunked(
        self,
        audio_path: Path,
        *,
        config: AppConfig,
        on_progress: Callable[[float], None] | None = None,
        window_seconds: float = 600.0,
        overlap_seconds: float = 2.0,
    ) -> list[TranscriptSegment]:
        try:
            total_dur = probe_duration(audio_path)
        except Exception:
            total_dur = 0.0
        ranges = compute_chunks(total_dur, window_seconds=window_seconds, overlap_seconds=overlap_seconds)
        if not ranges:
            return self._transcribe_single(audio_path, config=config, on_progress=on_progress)
        model = self._get_model(config)
        prompt = self._build_prompt(language=config.language)
        segments_out: list[TranscriptSegment] = []
        with tempfile.TemporaryDirectory(prefix="ytx-chunks-") as td:
            tdir = Path(td)
            n = len(ranges)
            for idx, (start, end) in enumerate(ranges):
                chunk_path = tdir / f"chunk_{idx:04d}.wav"
                slice_wav_segment(audio_path, chunk_path, start=start, end=end)
                file = self._upload_audio(chunk_path)
                resp = self._generate_with_retries(model, [file, prompt], timeout=getattr(config, 'transcribe_timeout', 600))
                payload_text = self._extract_text_from_response(resp)
                data = self._loads_json_loose(self._strip_code_fences(payload_text or "")) if payload_text else None
                segs = self._parse_segments_from_data_or_text(
                    data, payload_text, total_duration=(end - start)
                )
                # Offset by chunk start without mutating validated models to avoid
                # transient end<=start during assignment (pydantic validate_assignment).
                for s in segs:
                    new_start = float(start) + float(getattr(s, "start", 0.0) or 0.0)
                    new_end = float(start) + float(getattr(s, "end", 0.0) or 0.0)
                    if new_end <= new_start:
                        new_end = new_start + 0.001
                    segments_out.append(
                        TranscriptSegment(
                            id=len(segments_out),
                            start=new_start,
                            end=new_end,
                            text=str(getattr(s, "text", "")).strip(),
                            confidence=getattr(s, "confidence", None),
                        )
                    )
                if on_progress:
                    try:
                        on_progress(min(1.0, (idx + 1) / n))
                    except Exception:
                        pass
        # Stitch across chunk overlaps to remove duplicates and ensure continuity
        segments_out = stitch_segments(segments_out)
        return segments_out

    # --- Rate limit handling and retries (GEMINI-011) ---

    def _is_rate_limit_error(self, e: Exception) -> bool:
        msg = str(e).lower()
        try:
            from google.api_core import exceptions as gexc  # type: ignore

            for name in ("ResourceExhausted", "TooManyRequests"):
                cls = getattr(gexc, name, None)
                if cls is not None and isinstance(e, cls):
                    return True
        except Exception:
            pass
        return any(s in msg for s in ("rate limit", "quota", "exceeded", "too many requests", "429"))

    # use CloudEngineBase._generate_with_retries

    # --- Response parsing helpers (GEMINI-007) ---

    def _extract_text_from_response(self, resp) -> str | None:  # type: ignore[no-untyped-def]
        try:
            t = getattr(resp, "text", None)
            if t:
                return str(t)
            cands = getattr(resp, "candidates", None)
            if cands and len(cands) and getattr(cands[0], "content", None):
                parts = getattr(cands[0].content, "parts", None)
                if parts:
                    txt = "".join(str(getattr(p, "text", "")) for p in parts if getattr(p, "text", ""))
                    return txt or None
        except Exception:
            return None
        return None

    def _strip_code_fences(self, s: str) -> str:
        t = s.strip()
        if t.startswith("```"):
            # remove first line fence
            lines = t.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            # remove trailing fence if present
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return s

    def _loads_json_loose(self, s: str):  # type: ignore[no-untyped-def]
        if not s:
            return None
        try:
            import orjson as _orjson  # type: ignore

            return _orjson.loads(s)
        except Exception:
            pass
        import json as _json

        try:
            return _json.loads(s)
        except Exception:
            return None

    def _parse_time_seconds(self, v) -> float | None:  # type: ignore[no-untyped-def]
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            s = v.strip()
            # numeric string
            try:
                return float(s)
            except Exception:
                pass
            # HH:MM:SS(.mmm) or MM:SS(.mmm)
            parts = s.split(":")
            try:
                parts = [float(p) for p in parts]
            except Exception:
                return None
            if len(parts) == 3:
                h, m, sec = parts
            elif len(parts) == 2:
                h, m, sec = 0.0, parts[0], parts[1]
            else:
                return None
            return max(0.0, float(h) * 3600.0 + float(m) * 60.0 + float(sec))
        return None

    def _parse_segments_from_data_or_text(
        self,
        data: Any,
        text: str | None,
        *,
        total_duration: float = 0.0,
    ) -> list[TranscriptSegment]:
        # Accept either dict with "segments" or a list directly
        seg_list = None
        if isinstance(data, dict):
            for key in ("segments", "utterances", "items", "chunks"):
                val = data.get(key)
                if isinstance(val, list):
                    seg_list = val
                    break
        elif isinstance(data, list):
            seg_list = data

        results: list[TranscriptSegment] = []
        prev_end = 0.0
        if isinstance(seg_list, list):
            for entry in seg_list:
                if not isinstance(entry, dict):
                    # Sometimes entries may be strings
                    if isinstance(entry, str):
                        txt = entry.strip()
                        if txt:
                            start = prev_end
                            end = start + 0.001
                            results.append(TranscriptSegment(id=len(results), start=start, end=end, text=txt))
                            prev_end = end
                    continue
                # Accept multiple possible key names
                txt = (
                    str(
                        entry.get("text")
                        or entry.get("content")
                        or entry.get("transcript")
                        or entry.get("utterance")
                        or ""
                    )
                ).strip()
                if not txt:
                    continue
                start = self._parse_time_seconds(
                    entry.get("start")
                    or entry.get("start_time")
                    or entry.get("startTime")
                    or entry.get("start_sec")
                )
                end = self._parse_time_seconds(
                    entry.get("end")
                    or entry.get("end_time")
                    or entry.get("endTime")
                    or entry.get("end_sec")
                )
                if start is None:
                    start = prev_end
                if end is None:
                    end = start
                # Monotonic + minimal duration
                if start < prev_end:
                    start = prev_end
                if end <= start:
                    end = start + 0.001
                results.append(TranscriptSegment(id=len(results), start=float(start), end=float(end), text=txt))
                prev_end = float(end)

        if not results:
            # Fallback: treat entire response text as one segment if any text present
            text_fallback = (text or "").strip()
            if not text_fallback:
                raise EngineError("Gemini returned no usable content for transcription")
            results = [
                TranscriptSegment(
                    id=0, start=0.0, end=max(0.001, float(total_duration)), text=text_fallback
                )
            ]
        return results

    def detect_language(self, audio_path: Path, *, config: AppConfig) -> str | None:
        # Not yet implemented; may be inferred during transcription prompt later.
        return None


__all__ = ["GeminiEngine"]
