from __future__ import annotations

from pathlib import Path

from . import register_exporter
from .base import FileExporter, write_atomic
from ..models import TranscriptDoc


@register_exporter
class JSONExporter(FileExporter):
    name = "json"
    extension = ".json"

    def export(self, doc: TranscriptDoc, out_dir: Path) -> Path:
        path = self.target_path(doc, out_dir)
        # Use Pydantic's JSON with orjson configured in ModelBase for determinism
        data = doc.model_dump_json().encode("utf-8")
        return write_atomic(path, data)


__all__ = ["JSONExporter"]

