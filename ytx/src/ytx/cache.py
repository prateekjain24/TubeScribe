from __future__ import annotations

"""Cache path utilities and artifact existence checks.

Implements Phase 2 CACHE-001..003:
- CACHE-001: Create cache.py with path helpers and XDG cache root.
- CACHE-002: Build nested artifact directory path: video_id/engine/model/hash/.
- CACHE-003: Existence check for expected artifacts with basic integrity.

Default cache root follows XDG: $XDG_CACHE_HOME/ytx or ~/.cache/ytx.
Can be overridden via YTX_CACHE_DIR environment variable.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TYPE_CHECKING

if TYPE_CHECKING:  # avoid runtime import cycles
    from .config import AppConfig

# Expected artifact filenames within an artifact directory
META_JSON: Final[str] = "meta.json"
TRANSCRIPT_JSON: Final[str] = "transcript.json"
CAPTIONS_SRT: Final[str] = "captions.srt"


def _xdg_cache_home() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".cache"


def cache_root() -> Path:
    """Return the root cache directory for ytx.

    Resolution order:
    - YTX_CACHE_DIR (if set)
    - $XDG_CACHE_HOME/ytx
    - ~/.cache/ytx
    """
    override = os.environ.get("YTX_CACHE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return (_xdg_cache_home() / "ytx").resolve()


def _sanitize_segment(s: str) -> str:
    """Sanitize a path segment to be filesystem-friendly.

    Replaces path separators and whitespace/control chars with underscores and trims.
    """
    # Replace OS-specific separators and common unsafe chars
    bad = {"/", "\\", os.sep, os.altsep or ""}
    out = "".join("_" if (c in bad or ord(c) < 32) else c for c in s)
    out = out.strip().strip(".")
    # Avoid empty segments
    return out or "_"


@dataclass(frozen=True)
class ArtifactPaths:
    """Resolved artifact directory and file paths for a given key."""

    # Directory for this artifact set (video_id/engine/model/hash)
    dir: Path
    # Files inside the directory
    meta_json: Path
    transcript_json: Path
    captions_srt: Path


def build_artifact_dir(
    *,
    video_id: str,
    engine: str,
    model: str,
    config_hash: str,
    root: Path | None = None,
    create: bool = False,
) -> Path:
    """Return artifact directory path for the given key.

    Layout: <root>/<video_id>/<engine>/<model>/<config_hash>/
    If `create=True`, ensure the directory exists.
    """
    r = (root or cache_root())
    parts = (
        _sanitize_segment(video_id),
        _sanitize_segment(engine),
        _sanitize_segment(model),
        _sanitize_segment(config_hash),
    )
    d = r.joinpath(*parts)
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def build_artifact_paths(
    *,
    video_id: str,
    engine: str,
    model: str,
    config_hash: str,
    root: Path | None = None,
    create: bool = False,
) -> ArtifactPaths:
    """Return all artifact file paths for the given key.

    Does not create files; with `create=True`, ensures the directory exists.
    """
    d = build_artifact_dir(
        video_id=video_id,
        engine=engine,
        model=model,
        config_hash=config_hash,
        root=root,
        create=create,
    )
    return ArtifactPaths(
        dir=d,
        meta_json=d / META_JSON,
        transcript_json=d / TRANSCRIPT_JSON,
        captions_srt=d / CAPTIONS_SRT,
    )


def artifact_paths_for(
    *,
    video_id: str,
    config: "AppConfig",
    root: Path | None = None,
    create: bool = False,
) -> ArtifactPaths:
    """Convenience: build paths using fields from AppConfig.

    Uses `config.engine`, `config.model`, and `config.config_hash()`.
    """
    return build_artifact_paths(
        video_id=video_id,
        engine=config.engine,
        model=config.model,
        config_hash=config.config_hash(),
        root=root,
        create=create,
    )


def _nonempty_file(p: Path) -> bool:
    try:
        return p.is_file() and p.stat().st_size > 0
    except FileNotFoundError:
        return False


def artifacts_exist(paths: ArtifactPaths) -> bool:
    """Return True if all expected artifacts exist and look valid.

    Basic integrity: files must exist and be non-empty. Deeper validation,
    such as JSON parsing, happens in later tickets (CACHE-004).
    """
    return _nonempty_file(paths.transcript_json) and _nonempty_file(paths.captions_srt)


__all__ = [
    "META_JSON",
    "TRANSCRIPT_JSON",
    "CAPTIONS_SRT",
    "cache_root",
    "build_artifact_dir",
    "build_artifact_paths",
    "artifact_paths_for",
    "ArtifactPaths",
    "artifacts_exist",
]
