from __future__ import annotations

"""Application configuration (Pydantic BaseSettings, v2).

This covers only core runtime toggles for early phases. Environment
integration will be extended in later tickets (e.g., MODEL-008).
"""

from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from hashlib import sha256

try:
    import orjson as _orjson

    def _dumps(obj: Any) -> str:
        return _orjson.dumps(obj, option=_orjson.OPT_SORT_KEYS).decode()
except Exception:  # pragma: no cover
    import json as _json

    def _dumps(obj: Any) -> str:
        return _json.dumps(obj, sort_keys=True, separators=(",", ":"))


Engine = Literal["whisper", "gemini"]
Device = Literal["cpu", "auto", "cuda", "metal"]
ComputeType = Literal["auto", "int8", "int8_float16", "float16", "float32"]


class AppConfig(BaseSettings):
    """Config model for the CLI and pipeline."""

    engine: Engine = Field(default="whisper", description="Transcription engine")
    model: str = Field(default="small", description="Engine model name")
    language: str | None = Field(default=None, description="Target language or auto")
    device: Device = Field(default="cpu", description="Compute device")
    compute_type: ComputeType = Field(default="int8", description="Numerical precision for local models")

    # Later we can add cache/output dirs, concurrency, and API keys.

    # For now, only pick up variables starting with YTX_.
    model_config = SettingsConfigDict(env_prefix="YTX_", extra="ignore")

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
        }
        return {k: v for k, v in data.items() if v is not None}

    def config_hash(self) -> str:
        """Stable SHA256 hash for cache keying and artifact directories."""
        payload = _dumps(self._hash_input()).encode("utf-8")
        return sha256(payload).hexdigest()


__all__ = [
    "AppConfig",
    "Engine",
    "Device",
    "ComputeType",
]
