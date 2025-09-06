from __future__ import annotations

from pathlib import Path
from typing import Any

from . import register_exporter
from .base import FileExporter, write_atomic
from ..models import TranscriptDoc


@register_exporter
class JSONExporter(FileExporter):
    name = "json"
    extension = ".json"

    def __init__(self, *, indent: int | None = None) -> None:
        """JSON exporter with optional pretty indentation.

        - When `indent` is None (default), emits compact JSON using Pydantic's
          orjson-backed serializer with stable key order.
        - When `indent` is provided, tries to use orjson's OPT_INDENT_2 if
          `indent >= 2`, otherwise falls back to the stdlib `json.dumps` with
          the requested indent and `sort_keys=True`.
        """
        self.indent = indent

    def export(self, doc: TranscriptDoc, out_dir: Path) -> Path:
        path = self.target_path(doc, out_dir)
        if self.indent is None:
            data = doc.model_dump_json().encode("utf-8")
        else:
            try:
                import orjson as _orjson  # type: ignore

                payload: Any = doc.model_dump(mode="json")
                option = _orjson.OPT_SORT_KEYS
                if self.indent >= 2:
                    option |= _orjson.OPT_INDENT_2
                data = _orjson.dumps(payload, option=option)
            except Exception:
                import json as _json

                payload = doc.model_dump(mode="json")
                data = _json.dumps(payload, sort_keys=True, indent=self.indent, default=str).encode(
                    "utf-8"
                )
        return write_atomic(path, data)


__all__ = ["JSONExporter"]
