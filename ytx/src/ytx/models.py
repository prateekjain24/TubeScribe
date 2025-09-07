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
        return _orjson.dumps(v, default=default, option=_orjson.OPT_SORT_KEYS).decode()

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


# Video metadata
import re
from pydantic import field_validator


def _parse_iso8601_duration(s: str) -> float:
    """Parse subset of ISO8601 durations like PT1H2M3S → seconds.

    Supports P, PT, with H/M/S components. Ignores days/months/years.
    """
    pattern = re.compile(r"PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?")
    m = pattern.fullmatch(s)
    if not m:
        raise ValueError("Invalid ISO8601 duration")
    hours = int(m.group("h") or 0)
    minutes = int(m.group("m") or 0)
    seconds = int(m.group("s") or 0)
    return float(hours * 3600 + minutes * 60 + seconds)


def _parse_hhmmss(s: str) -> float:
    parts = s.split(":")
    if not all(p.isdigit() for p in parts):
        raise ValueError("Invalid time string")
    parts = [int(p) for p in parts]
    if len(parts) == 3:
        h, m, sec = parts
    elif len(parts) == 2:
        h, m, sec = 0, parts[0], parts[1]
    elif len(parts) == 1:
        h, m, sec = 0, 0, parts[0]
    else:
        raise ValueError("Invalid time components")
    return float(h * 3600 + m * 60 + sec)


class VideoMetadata(ModelBase):
    """Metadata about the source video/audio used for transcription."""

    id: NonEmptyStr
    title: str | None = None
    duration: Seconds | None = None
    url: NonEmptyStr
    uploader: str | None = None
    description: str | None = None
    chapters: list[Chapter] | None = None

    @field_validator("duration", mode="before")
    @classmethod
    def _coerce_duration(cls, v):  # type: ignore[override]
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            txt = v.strip().upper()
            # ISO8601 like PT1H2M3S
            if txt.startswith("PT"):
                return _parse_iso8601_duration(txt)
            # HH:MM:SS or MM:SS
            return _parse_hhmmss(txt)
        raise TypeError("Unsupported duration type")


__all__.append("VideoMetadata")
