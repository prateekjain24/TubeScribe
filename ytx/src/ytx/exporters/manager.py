from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from . import available_exporters, get_exporter
from ..models import TranscriptDoc


def _ensure_registry_loaded() -> None:
    """Import built-in exporters to populate the registry."""
    # Safe to import multiple times; registration is idempotent.
    try:
        from . import json_exporter  # noqa: F401
    except Exception:
        pass
    try:
        from . import srt_exporter  # noqa: F401
    except Exception:
        pass
    try:
        from . import markdown_exporter  # noqa: F401
    except Exception:
        pass


def parse_formats(spec: str | None) -> list[str]:
    """Parse a comma-separated exporter list (e.g., "json,srt,vtt").

    Returns a normalized list filtered to registered exporters. If `spec` is
    None or empty, returns all available exporters.
    """
    _ensure_registry_loaded()
    names = set(available_exporters())
    if not spec:
        return sorted(names)
    parts = [p.strip().lower() for p in spec.split(",") if p.strip()]
    # Filter only registered exporters, preserve order but drop duplicates
    seen: set[str] = set()
    result: list[str] = []
    for p in parts:
        if p in names and p not in seen:
            result.append(p)
            seen.add(p)
    return result


def export_all(doc: TranscriptDoc, out_dir: Path, formats: Iterable[str]) -> list[Path]:
    """Export `doc` with each exporter in `formats`, returning written paths.

    Each exporter is instantiated with default options. For exporters requiring
    custom settings (e.g., JSON indent), callers may use those classes directly.
    """
    _ensure_registry_loaded()
    out: list[Path] = []
    for name in formats:
        cls = get_exporter(name)
        exporter = cls()  # type: ignore[call-arg]
        path = exporter.export(doc, out_dir)
        out.append(path)
    return out


__all__ = [
    "parse_formats",
    "export_all",
]
