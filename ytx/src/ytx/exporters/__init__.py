from __future__ import annotations

"""Exporter interface and minimal registry.

Exporters turn a TranscriptDoc into concrete artifacts (JSON, SRT, VTT, TXT).
Each exporter implements `export(doc, out_dir) -> Path` and declares a unique
`name` (e.g., "json") and file `extension` (e.g., ".json").
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Type

from ..models import TranscriptDoc


class Exporter(ABC):
    """Abstract base class for exporters."""

    #: Unique short name (e.g., "json", "srt", "vtt", "txt").
    name: str
    #: Default file extension including dot (e.g., ".json").
    extension: str

    @abstractmethod
    def export(self, doc: TranscriptDoc, out_dir: Path) -> Path:
        """Export `doc` to `out_dir` and return the written file path."""
        raise NotImplementedError


_REGISTRY: Dict[str, Type[Exporter]] = {}


def register_exporter(cls: Type[Exporter]) -> Type[Exporter]:
    """Class decorator to register an exporter by its `name`.

    Example:
        @register_exporter
        class JSONExporter(Exporter):
            name = "json"
            extension = ".json"
            ...
    """
    key = getattr(cls, "name", None)
    if not key or not isinstance(key, str):
        raise ValueError("Exporter must define a string `name` attribute")
    _REGISTRY[key] = cls
    return cls


def get_exporter(name: str) -> Type[Exporter]:
    try:
        return _REGISTRY[name]
    except KeyError as e:
        raise KeyError(f"unknown exporter '{name}'") from e


def available_exporters() -> list[str]:
    return sorted(_REGISTRY)


__all__ = [
    "Exporter",
    "register_exporter",
    "get_exporter",
    "available_exporters",
]

