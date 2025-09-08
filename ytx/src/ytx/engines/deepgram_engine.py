from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
import os
import json as _json

from .base import TranscriptionEngine, EngineError
from .cloud_base import CloudEngineBase
from ..config import AppConfig
from ..models import TranscriptSegment
from ..chunking import compute_chunks, slice_wav_segment
from ..stitch import stitch_segments


def _load_api_key() -> str:
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        raise EngineError(code="ENGINE", message="DEEPGRAM_API_KEY is not set in the environment")
    return key


class DeepgramEngine(CloudEngineBase, TranscriptionEngine):
    name = "deepgram"

    def _prefer_sdk(self) -> bool:
        return os.environ.get("YTX_PREFER_SDK", "").lower() in ("1", "true", "yes")

    def transcribe(self, audio_path: Path, *, config: AppConfig, on_progress: Callable[[float], None] | None = None) -> list[TranscriptSegment]:
        window = 600.0
        overlap = 2.0
        try:
            from ..audio import probe_duration

            duration = probe_duration(audio_path)
        except Exception:
            duration = 0.0
        if config.timestamp_policy == "chunked" or duration > window:
            return self._transcribe_chunked(audio_path, config=config, on_progress=on_progress, window_seconds=window, overlap_seconds=overlap)
        return self._transcribe_single(audio_path, config=config, on_progress=on_progress)

    def _endpoint(self, cfg: AppConfig) -> str:
        base = "https://api.deepgram.com/v1/listen"
        # Build query params from engine_options
        opts = cfg.engine_options or {}
        params = []
        if opts.get("utterances", True):
            params.append("utterances=true")
        if opts.get("smart_format", True):
            params.append("smart_format=true")
        if "model" in opts:
            params.append(f"model={opts['model']}")
        return base + ("?" + "&".join(params) if params else "")

    def _transcribe_single(self, audio_path: Path, *, config: AppConfig, on_progress: Callable[[float], None] | None = None) -> list[TranscriptSegment]:
        key = _load_api_key()
        # Try SDK first (optional), fallback to HTTP
        if self._prefer_sdk():
            segs = self._try_sdk_transcribe(audio_path, config=config)
            if segs is not None:
                return segs
        endpoint = self._endpoint(config)
        headers = {
            "Authorization": f"Token {key}",
            "Content-Type": "audio/wav",
        }
        data = Path(audio_path).read_bytes()
        r = self._http_post_with_retries(endpoint, headers=headers, data=data, timeout=getattr(config, 'transcribe_timeout', 600))
        try:
            payload = r.json()
        except Exception:
            return []
        segs = self._parse_deepgram_segments(payload)
        if not segs:
            # Fallback to transcript text
            alt = (((payload.get("results") or {}).get("channels") or [{}])[0].get("alternatives") or [{}])[0]
            txt = alt.get("transcript", "").strip()
            end = self._probe_duration_safe(audio_path)
            return [TranscriptSegment(id=0, start=0.0, end=end or 0.001, text=txt)]
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
        with __import__('tempfile').TemporaryDirectory(prefix='ytx-deepgram-chunks-') as td:  # type: ignore
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

    def _parse_deepgram_segments(self, payload: dict[str, Any]) -> list[TranscriptSegment]:
        segs: list[TranscriptSegment] = []
        res = payload.get("results") or {}
        chans = res.get("channels") or []
        if not chans:
            return []
        alt = chans[0].get("alternatives") or []
        if not alt:
            return []
        utterances = alt[0].get("utterances") or []
        prev_end = 0.0
        for u in utterances:
            try:
                start = float(u.get("start", prev_end))
                end = float(u.get("end", start))
                txt = str(u.get("transcript") or "").strip()
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

    def _try_sdk_transcribe(self, audio_path: Path, *, config: AppConfig) -> list[TranscriptSegment] | None:
        try:
            # Deepgram SDK v3
            from deepgram import DeepgramClient  # type: ignore
        except Exception:
            return None
        try:
            os.environ.setdefault("DEEPGRAM_API_KEY", _load_api_key())
            client = DeepgramClient()  # type: ignore
            # Options mapping
            opts = config.engine_options or {}
            options: dict[str, Any] = {}
            if opts.get("utterances", True):
                options["utterances"] = True
            if opts.get("smart_format", True):
                options["smart_format"] = True
            if "model" in opts:
                options["model"] = opts["model"]
            # Read file and send
            with open(audio_path, 'rb') as f:
                buf = f.read()
            # Some SDKs use: client.listen.prerecorded.v("1").transcribe_file
            # Try a generic call signature; if it fails, fallback to HTTP.
            try:
                result = client.listen.prerecorded.v('1').transcribe_file(  # type: ignore[attr-defined]
                    {'buffer': buf, 'mimetype': 'audio/wav'},
                    options
                )
            except Exception:
                return None
        except Exception:
            return None
        # Extract JSON and parse utterances
        try:
            if hasattr(result, 'to_dict'):
                payload = result.to_dict()  # type: ignore[attr-defined]
            else:
                payload = result  # assume dict
        except Exception:
            return None
        segs = self._parse_deepgram_segments(payload)
        if not segs:
            alt = (((payload.get("results") or {}).get("channels") or [{}])[0].get("alternatives") or [{}])[0]
            txt = alt.get("transcript", "").strip()
            end = self._probe_duration_safe(audio_path)
            return [TranscriptSegment(id=0, start=0.0, end=end or 0.001, text=txt)]
        return segs
