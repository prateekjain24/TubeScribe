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
from datetime import datetime, timezone
import tempfile
import json as _json

if TYPE_CHECKING:  # avoid runtime import cycles
    from .config import AppConfig
    from .models import TranscriptDoc, VideoMetadata

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


# --- CACHE-004: Artifact Reader ---


class CacheError(RuntimeError):
    pass


class CacheCorruptedError(CacheError):
    pass


def _read_json_bytes(path: Path) -> bytes:
    try:
        return Path(path).read_bytes()
    except FileNotFoundError as e:
        raise CacheError(f"missing cache file: {path}") from e
    except Exception as e:  # pragma: no cover
        raise CacheError(f"failed reading cache file: {path}: {e}") from e


def _loads_json(data: bytes):  # type: ignore[no-untyped-def]
    try:
        import orjson as _orjson  # type: ignore

        return _orjson.loads(data)
    except Exception:
        return _json.loads(data.decode("utf-8"))


def read_transcript_doc(paths: ArtifactPaths) -> "TranscriptDoc":
    """Load and validate TranscriptDoc from cached transcript.json.

    Raises CacheError on missing file, CacheCorruptedError on parse/validation failure.
    """
    from .models import TranscriptDoc  # local import to avoid cycles

    raw = _read_json_bytes(paths.transcript_json)
    try:
        payload = _loads_json(raw)
        return TranscriptDoc.model_validate(payload)
    except Exception as e:
        raise CacheCorruptedError(f"corrupted transcript.json at {paths.transcript_json}: {e}") from e


def read_meta(paths: ArtifactPaths) -> dict:
    """Load meta.json as a plain dict.

    Returns a dict; raises CacheError/CacheCorruptedError similarly to transcript reader.
    """
    raw = _read_json_bytes(paths.meta_json)
    try:
        return _loads_json(raw)
    except Exception as e:
        raise CacheCorruptedError(f"corrupted meta.json at {paths.meta_json}: {e}") from e


# --- CACHE-005: Atomic Write Operations ---


def write_bytes_atomic(path: Path, data: bytes) -> Path:
    """Atomically write bytes to path using temp file then rename.

    Creates parent directories as needed and fsyncs the temporary file before replace().
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)
    return path


# --- CACHE-006: Cache Metadata ---


def _ytx_version() -> str:
    try:
        from importlib.metadata import version

        return version("ytx")
    except Exception:
        return "0.1.0"


def build_meta_payload(
    *,
    video_id: str,
    config: "AppConfig",
    source: "VideoMetadata | None" = None,
) -> dict:
    """Build a meta.json payload with creation info, version, and source.

    Includes: created_at (UTC ISO8601 Z), ytx_version, video_id, engine, model, config_hash,
    and optional source (url, title, duration, uploader).
    """
    payload: dict = {
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ytx_version": _ytx_version(),
        "video_id": video_id,
        "engine": config.engine,
        "model": config.model,
        "config_hash": config.config_hash(),
    }
    if source is not None:
        payload["source"] = {
            "url": source.url,
            "title": source.title,
            "duration": source.duration,
            "uploader": source.uploader,
        }
    return payload


def write_meta(paths: ArtifactPaths, payload: dict) -> Path:
    """Write meta.json atomically."""
    try:
        import orjson as _orjson  # type: ignore

        data = _orjson.dumps(payload, option=_orjson.OPT_SORT_KEYS)
    except Exception:
        data = _json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return write_bytes_atomic(paths.meta_json, data) 


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
    "CacheError",
    "CacheCorruptedError",
    "read_transcript_doc",
    "read_meta",
    "write_bytes_atomic",
    "build_meta_payload",
    "write_meta",
]
