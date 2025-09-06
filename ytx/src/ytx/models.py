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

