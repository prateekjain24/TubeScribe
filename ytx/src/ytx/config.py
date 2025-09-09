from __future__ import annotations

"""Application configuration (Pydantic BaseSettings, v2).

This covers only core runtime toggles for early phases. Environment
integration will be extended in later tickets (e.g., MODEL-008).
"""

from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from hashlib import sha256

try:
    import orjson as _orjson

    def _dumps(obj: Any) -> str:
        return _orjson.dumps(obj, option=_orjson.OPT_SORT_KEYS).decode()
except Exception:  # pragma: no cover
    import json as _json

    def _dumps(obj: Any) -> str:
        return _json.dumps(obj, sort_keys=True, separators=(",", ":"))


# Engines recognized by the CLI. Local: whisper/whispercpp; Cloud: gemini/openai/deepgram/elevenlabs
Engine = Literal["whisper", "whispercpp", "gemini", "openai", "deepgram", "elevenlabs"]
Device = Literal["cpu", "auto", "cuda", "metal"]
ComputeType = Literal["auto", "int8", "int8_float16", "float16", "float32"]
TimestampPolicy = Literal["native", "chunked", "none"]


class AppConfig(BaseSettings):
    """Config model for the CLI and pipeline."""

    engine: Engine = Field(default="whisper", description="Transcription engine")
    model: str = Field(default="large-v3-turbo", description="Engine model name")
    language: str | None = Field(default=None, description="Target language or auto")
    device: Device = Field(default="cpu", description="Compute device")
    compute_type: ComputeType = Field(default="int8", description="Numerical precision for local models")
    # Cross-provider options
    timestamp_policy: TimestampPolicy = Field(default="native", description="Timestamp handling policy")
    engine_options: dict[str, Any] = Field(default_factory=dict, description="Provider-specific options")
    # Timeouts (seconds)
    network_timeout: int = Field(default=90, description="Metadata/network timeout (s)")
    download_timeout: int = Field(default=1800, description="Download timeout (s)")
    transcribe_timeout: int = Field(default=600, description="Transcription API timeout (s)")
    summarize_timeout: int = Field(default=180, description="Summarization API timeout (s)")

    # whisper.cpp (Metal) settings
    whispercpp_bin: str = Field(default="main", description="Path or name of whisper.cpp binary (main)")
    whispercpp_ngl: int = Field(default=35, description="Number of layers to offload to GPU (Metal)")
    whispercpp_threads: int | None = Field(default=None, description="Threads for whisper.cpp; defaults to CPU count")

    # Downloader controls
    max_download_abr_kbps: int | None = Field(
        default=96,
        description="Cap YouTube audio bitrate (kbps) during download; set to 0/None to disable",
    )

    # Later we can add cache/output dirs, concurrency, and API keys.

    # For now, only pick up variables starting with YTX_.
    model_config = SettingsConfigDict(env_prefix="YTX_", extra="ignore", env_file=(".env",), env_file_encoding="utf-8")

    # --- Hashing ---
    def _hash_input(self) -> dict[str, Any]:
        """Subset of fields that affect deterministic outputs.

        Excludes secrets and ephemeral values. Extend as features grow.
        """
        data = {
            "engine": self.engine,
            "model": self.model,
            "language": self.language,
            "device": self.device,
            "compute_type": self.compute_type,
            "timestamp_policy": self.timestamp_policy,
            "engine_options": self.engine_options or {},
        }
        # Engine-specific knobs that impact output determinism
        if self.engine == "whispercpp":
            data.update({
                "wc_bin": self.whispercpp_bin,
                "wc_ngl": self.whispercpp_ngl,
                "wc_threads": self.whispercpp_threads or 0,
            })
        return {k: v for k, v in data.items() if v is not None}

    def config_hash(self) -> str:
        """Stable SHA256 hash for cache keying and artifact directories."""
        payload = _dumps(self._hash_input()).encode("utf-8")
        return sha256(payload).hexdigest()


def load_config(**overrides: Any) -> AppConfig:
    """Load environment from .env (non-overriding) and return AppConfig.

    python-dotenv is used with override=False so real env vars take precedence.
    Explicit keyword overrides win over both.
    """
    load_dotenv(override=False)
    return AppConfig(**overrides)


__all__ = [
    "AppConfig",
    "Engine",
    "Device",
    "ComputeType",
    "TimestampPolicy",
]
