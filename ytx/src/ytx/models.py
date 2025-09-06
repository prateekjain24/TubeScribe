"""Core models foundation (Pydantic v2).

Provides a shared BaseModel config and common type aliases used across
transcript, chapter, and configuration models.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

try:  # Prefer orjson for fast, stable JSON
    import orjson as _orjson

    def _orjson_dumps(v, *, default):  # type: ignore[no-redef]
        return _orjson.dumps(v, default=default).decode()

except Exception:  # pragma: no cover - fallback to stdlib
    import json as _json

    def _orjson_dumps(v, *, default):  # type: ignore[no-redef]
        return _json.dumps(v, default=default)


class ModelBase(BaseModel):
    """Shared Pydantic base with strict, predictable behavior."""

    model_config = ConfigDict(
        extra="forbid",  # reject unknown fields
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=True,
        populate_by_name=True,
        arbitrary_types_allowed=False,
        ser_json_timedelta="iso8601",
        ser_json_bytes="utf8",
        ser_json_dumps=_orjson_dumps,
    )


# Common type aliases
Seconds = Annotated[float, Field(ge=0.0, description="Time in seconds (>= 0)")]
NonEmptyStr = Annotated[str, Field(min_length=1, strip_whitespace=True)]


__all__ = [
    "ModelBase",
    "Seconds",
    "NonEmptyStr",
]


# Transcript models
from pydantic import Field, model_validator


class TranscriptSegment(ModelBase):
    """A continuous spoken segment with timing and text.

    Notes on confidence:
    - Range and meaning depend on engine. For Whisper it may be a log-probability
      (often negative). For LLM-based engines it may be omitted.
    """

    id: int = Field(ge=0)
    start: Seconds
    end: Seconds
    text: NonEmptyStr
    confidence: float | None = None

    @model_validator(mode="after")
    def _validate_times(self) -> "TranscriptSegment":
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self

    @property
    def duration(self) -> float:
        return float(self.end - self.start)


__all__.append("TranscriptSegment")


class Chapter(ModelBase):
    """A logical chapter boundary within the source audio/video."""

    title: NonEmptyStr | None = None
    start: Seconds
    end: Seconds
    summary: str | None = None

    @model_validator(mode="after")
    def _validate_times(self) -> "Chapter":
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self

    @property
    def duration(self) -> float:
        return float(self.end - self.start)


__all__.append("Chapter")


class Summary(ModelBase):
    """Abstractive summary of a transcript or chapter."""

    tldr: NonEmptyStr = Field(max_length=500)
    bullets: list[NonEmptyStr] = Field(default_factory=list)


__all__.append("Summary")


from datetime import datetime


class TranscriptDoc(ModelBase):
    """Top-level transcript document with metadata and segments."""

    # Metadata
    video_id: NonEmptyStr
    source_url: NonEmptyStr
    title: str | None = None
    duration: Seconds | None = None
    language: str | None = None
    engine: NonEmptyStr
    model: NonEmptyStr
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Content
    segments: list[TranscriptSegment]
    chapters: list[Chapter] | None = None
    summary: Summary | None = None


__all__.append("TranscriptDoc")
