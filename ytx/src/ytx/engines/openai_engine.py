from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import os
import mimetypes
import json as _json

from .base import TranscriptionEngine, EngineError
from .cloud_base import CloudEngineBase
from ..config import AppConfig
from ..models import TranscriptSegment
from ..chunking import compute_chunks, slice_wav_segment
from ..stitch import stitch_segments


def _load_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EngineError(code="ENGINE", message="OPENAI_API_KEY is not set in the environment")
    if not (key.startswith("sk-") and len(key) > 20):  # light validation
        raise EngineError(code="ENGINE", message="OPENAI_API_KEY format appears invalid")
    return key


class OpenAIEngine(CloudEngineBase, TranscriptionEngine):
    name = "openai"

    def transcribe(self, audio_path: Path, *, config: AppConfig, on_progress: Callable[[float], None] | None = None) -> list[TranscriptSegment]:
        # Decide chunking
        window = 600.0
        overlap = 2.0
        try:
            from ..audio import probe_duration

            duration = probe_duration(audio_path)
        except Exception:
            duration = 0.0
        if config.timestamp_policy == "chunked" or duration > window:
            return self._transcribe_chunked(audio_path, config=config, on_progress=on_progress, window_seconds=window, overlap_seconds=overlap)
        segs = self._transcribe_single(audio_path, config=config, on_progress=on_progress)
        if config.timestamp_policy == "none":
            text = " ".join(s.text for s in segs if s.text).strip()
            end = max((s.end for s in segs), default=duration)
            return [TranscriptSegment(id=0, start=0.0, end=max(0.001, float(end)), text=text)]
        return segs

    def _endpoint(self) -> str:
        # OpenAI Whisper transcription endpoint
        return "https://api.openai.com/v1/audio/transcriptions"

    def _model_name(self, cfg: AppConfig) -> str:
        # Accept override via cfg.model, default to whisper-1
        m = (cfg.model or "whisper-1").strip()
        return m if m else "whisper-1"

    def _prefer_sdk(self) -> bool:
        return os.environ.get("YTX_PREFER_SDK", "").lower() in ("1", "true", "yes")

    def _transcribe_single(self, audio_path: Path, *, config: AppConfig, on_progress: Callable[[float], None] | None = None) -> list[TranscriptSegment]:
        key = _load_api_key()
        endpoint = self._endpoint()
        model = self._model_name(config)
        mime = mimetypes.guess_type(str(audio_path))[0] or "audio/wav"
        # Try SDK first (optional), then fallback to HTTP
        if self._prefer_sdk():
            segs = self._try_sdk_transcribe(audio_path, model=model, language=config.language, timeout=getattr(config, 'transcribe_timeout', 600))
            if segs is not None:
                return segs
        headers = {"Authorization": f"Bearer {key}"}
        files = {
            "file": (Path(audio_path).name, open(audio_path, "rb"), mime),
        }
        data = {
            "model": model,
            "response_format": "verbose_json",  # attempt structured segments
        }
        if config.language:
            data["language"] = config.language
        # Map engine options if any
        for k, v in (config.engine_options or {}).items():
            if isinstance(v, (str, int, float)):
                data[str(k)] = str(v)

        r = self._http_post_with_retries(endpoint, headers=headers, files=files, data=data, timeout=getattr(config, 'transcribe_timeout', 600))
        try:
            payload = r.json()
        except Exception:
            # Fallback plain text
            txt = r.text.strip()
            end = self._probe_duration_safe(audio_path)
            return [TranscriptSegment(id=0, start=0.0, end=end or 0.001, text=txt)]
        segs = self._parse_openai_verbose_segments(payload)
        if not segs:
            txt = payload.get("text") or ""
            end = self._probe_duration_safe(audio_path)
            return [TranscriptSegment(id=0, start=0.0, end=end or 0.001, text=txt.strip())]
        return segs

    def _transcribe_chunked(self, audio_path: Path, *, config: AppConfig, on_progress: Callable[[float], None] | None = None, window_seconds: float = 600.0, overlap_seconds: float = 2.0) -> list[TranscriptSegment]:
        try:
            from ..audio import probe_duration

            total = probe_duration(audio_path)
        except Exception:
            total = 0.0
        ranges = compute_chunks(total, window_seconds=window_seconds, overlap_seconds=overlap_seconds)
        if not ranges:
            return self._transcribe_single(audio_path, config=config, on_progress=on_progress)
        segs_out: list[TranscriptSegment] = []
        with \
            __import__('tempfile').TemporaryDirectory(prefix='ytx-openai-chunks-') as td:  # type: ignore
            tdir = Path(td)
            for idx, (start, end) in enumerate(ranges):
                chunk = tdir / f"chunk_{idx:04d}.wav"
                slice_wav_segment(audio_path, chunk, start=start, end=end)
                segs = self._transcribe_single(chunk, config=config, on_progress=None)
                # Avoid in-place mutation of validated models; construct new instances
                for s in segs:
                    new_start = float(start) + float(getattr(s, "start", 0.0) or 0.0)
                    new_end = float(start) + float(getattr(s, "end", 0.0) or 0.0)
                    if new_end <= new_start:
                        new_end = new_start + 0.001
                    segs_out.append(
                        TranscriptSegment(
                            id=len(segs_out),
                            start=new_start,
                            end=new_end,
                            text=str(getattr(s, "text", "")).strip(),
                            confidence=getattr(s, "confidence", None),
                        )
                    )
                if on_progress:
                    try:
                        on_progress(min(1.0, (idx + 1) / max(1, len(ranges))))
                    except Exception:
                        pass
        return stitch_segments(segs_out)

    def _parse_openai_verbose_segments(self, payload: dict[str, Any]) -> list[TranscriptSegment]:
        segs: list[TranscriptSegment] = []
        data = payload.get("segments")
        if isinstance(data, list):
            prev_end = 0.0
            for i, entry in enumerate(data):
                try:
                    start = float(entry.get("start", prev_end))
                    end = float(entry.get("end", start))
                    txt = str(entry.get("text") or "").strip()
                except Exception:
                    continue
                if not txt:
                    continue
                if start < prev_end:
                    start = prev_end
                if end <= start:
                    end = start + 0.001
                prev_end = end
                segs.append(TranscriptSegment(id=len(segs), start=start, end=end, text=txt))
        return segs

    def _probe_duration_safe(self, path: Path) -> float:
        try:
            from ..audio import probe_duration

            return float(probe_duration(path))
        except Exception:
            return 0.0

    def _try_sdk_transcribe(self, audio_path: Path, *, model: str, language: str | None, timeout: int) -> list[TranscriptSegment] | None:
        try:
            # Lazy import OpenAI SDK v1+ interface
            from openai import OpenAI  # type: ignore
        except Exception:
            return None
        try:
            # Ensure SDK can see the key
            os.environ.setdefault("OPENAI_API_KEY", _load_api_key())
            client = OpenAI()
            with open(audio_path, "rb") as f:
                # Attempt verbose JSON for segments; fallback will be handled if not supported
                resp = client.audio.transcriptions.create(  # type: ignore[attr-defined]
                    model=model,
                    file=f,
                    response_format="verbose_json",
                    language=language or None,
                )
        except Exception:
            return None
        # Try to get segments from SDK response
        payload: dict[str, Any] | None = None
        try:
            # Some SDK objects have .model_dump_json() / .to_dict(); fallback to attribute mapping
            if hasattr(resp, "model_dump_json"):
                payload = _json.loads(resp.model_dump_json())  # type: ignore[attr-defined]
            elif hasattr(resp, "to_dict"):
                payload = resp.to_dict()  # type: ignore[attr-defined]
            else:
                # best-effort: common attributes
                payload = {"text": getattr(resp, "text", ""), "segments": getattr(resp, "segments", None)}
        except Exception:
            payload = None
        if not payload:
            # plain text case
            txt = str(getattr(resp, "text", "")).strip()
            end = self._probe_duration_safe(audio_path)
            return [TranscriptSegment(id=0, start=0.0, end=end or 0.001, text=txt)]
        segs = self._parse_openai_verbose_segments(payload)
        if not segs:
            txt = str(payload.get("text") or "").strip()
            end = self._probe_duration_safe(audio_path)
            return [TranscriptSegment(id=0, start=0.0, end=end or 0.001, text=txt)]
        return segs
