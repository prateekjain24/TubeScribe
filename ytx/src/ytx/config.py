from __future__ import annotations

"""Application configuration (Pydantic BaseSettings, v2).

This covers only core runtime toggles for early phases. Environment
integration will be extended in later tickets (e.g., MODEL-008).
"""

from typing import Literal

from pydantic import BaseSettings, Field
from pydantic_settings import SettingsConfigDict


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


__all__ = [
    "AppConfig",
    "Engine",
    "Device",
    "ComputeType",
]

