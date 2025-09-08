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
from typing import Final, TYPE_CHECKING, Iterator
from datetime import datetime, timezone
import tempfile
import json as _json
import shutil

if TYPE_CHECKING:  # avoid runtime import cycles
    from .config import AppConfig
    from .models import TranscriptDoc, VideoMetadata

# Expected artifact filenames within an artifact directory
META_JSON: Final[str] = "meta.json"
TRANSCRIPT_JSON: Final[str] = "transcript.json"
CAPTIONS_SRT: Final[str] = "captions.srt"
SUMMARY_JSON: Final[str] = "summary.json"


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
    summary_json: Path


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
        summary_json=d / SUMMARY_JSON,
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
    """Return True if expected artifacts exist and look valid.

    Accepts either canonical names (transcript.json, captions.srt) or
    legacy/video-id based names (<video_id>.json/.srt) to ensure backwards
    compatibility with previously written artifacts.
    """
    # canonical
    json_ok = _nonempty_file(paths.transcript_json)
    srt_ok = _nonempty_file(paths.captions_srt)
    if json_ok and srt_ok:
        return True
    # fallback to <video_id>.json/.srt
    try:
        # <root>/<video_id>/<engine>/<model>/<hash>
        vid = paths.dir.parents[2].name
    except Exception:
        vid = None
    if vid:
        if not json_ok:
            json_ok = _nonempty_file(paths.dir / f"{vid}.json")
        if not srt_ok:
            srt_ok = _nonempty_file(paths.dir / f"{vid}.srt")
    return json_ok and srt_ok


# --- CACHE-004: Artifact Reader ---


from .errors import FileSystemError, YTXError


class CacheError(FileSystemError):
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

    try:
        raw = _read_json_bytes(paths.transcript_json)
    except CacheError:
        # Fallback to <video_id>.json if present
        vid = None
        try:
            vid = paths.dir.parents[2].name
        except Exception:
            pass
        if vid:
            raw = _read_json_bytes(paths.dir / f"{vid}.json")
        else:
            raise
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


def write_summary(paths: ArtifactPaths, payload: dict) -> Path:
    """Write summary.json atomically."""
    try:
        import orjson as _orjson  # type: ignore

        data = _orjson.dumps(payload, option=_orjson.OPT_SORT_KEYS)
    except Exception:
        data = _json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return write_bytes_atomic(paths.summary_json, data)


def read_summary(paths: ArtifactPaths) -> dict | None:
    try:
        raw = _read_json_bytes(paths.summary_json)
    except CacheError:
        return None
    try:
        return _loads_json(raw)
    except Exception:
        return None


# --- CACHE-005: Atomic Write Operations ---


def write_bytes_atomic(path: Path, data: bytes) -> Path:
    """Atomically write bytes to path using temp file then rename.

    Creates parent directories as needed and fsyncs the temporary file before replace().
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)
        return path
    except OSError as e:
        raise FileSystemError(f"atomic write failed: {path}", cause=e)


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
    provider: str | None = None,
    request_id: str | None = None,
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
    if provider:
        payload["provider"] = provider
    if request_id:
        payload["request_id"] = request_id
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


# -------- Listing, Stats, and Expiration (CACHE-007..010) --------


@dataclass(frozen=True)
class CacheEntry:
    dir: Path
    video_id: str
    engine: str
    model: str
    config_hash: str
    created_at: datetime | None
    size_bytes: int
    title: str | None = None
    url: str | None = None


def _parse_iso8601_z(s: str) -> datetime | None:
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def dir_size(path: Path) -> int:
    total = 0
    try:
        for p in Path(path).rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except FileNotFoundError:
                pass
    except FileNotFoundError:
        return 0
    return total


def iter_artifact_dirs(root: Path | None = None) -> Iterator[Path]:
    r = (root or cache_root())
    if not r.exists():
        return iter(())
    for video_dir in r.iterdir():
        if not video_dir.is_dir():
            continue
        for engine_dir in video_dir.iterdir():
            if not engine_dir.is_dir():
                continue
            for model_dir in engine_dir.iterdir():
                if not model_dir.is_dir():
                    continue
                for hash_dir in model_dir.iterdir():
                    if hash_dir.is_dir():
                        yield hash_dir


def scan_cache(root: Path | None = None) -> list[CacheEntry]:
    entries: list[CacheEntry] = []
    for d in iter_artifact_dirs(root):
        try:
            # <root>/<video_id>/<engine>/<model>/<hash>
            video_id = d.parents[2].name
            engine = d.parents[1].name
            model = d.parents[0].name
            cfg_hash = d.name
        except Exception:
            continue
        paths = ArtifactPaths(
            dir=d,
            meta_json=d / META_JSON,
            transcript_json=d / TRANSCRIPT_JSON,
            captions_srt=d / CAPTIONS_SRT,
            summary_json=d / SUMMARY_JSON,
        )
        if not artifacts_exist(paths):
            continue
        created_at: datetime | None = None
        title: str | None = None
        url: str | None = None
        if paths.meta_json.exists():
            try:
                meta = read_meta(paths)
                created_at = _parse_iso8601_z(str(meta.get("created_at", "")))
                src = meta.get("source") or {}
                title = src.get("title")
                url = src.get("url")
            except Exception:
                pass
        entries.append(
            CacheEntry(
                dir=d,
                video_id=video_id,
                engine=engine,
                model=model,
                config_hash=cfg_hash,
                created_at=created_at,
                size_bytes=dir_size(d),
                title=title,
                url=url,
            )
        )
    return entries


def clear_cache(root: Path | None = None, *, video_id: str | None = None) -> tuple[int, int]:
    """Clear entire cache or a specific video's cache subtree.

    Returns (removed_dir_count, freed_bytes).
    """
    r = (root or cache_root())
    if not r.exists():
        return (0, 0)
    targets: list[Path] = []
    if video_id:
        target = r / _sanitize_segment(video_id)
        if target.exists() and target.is_dir():
            targets.append(target)
    else:
        targets.append(r)
    removed = 0
    freed = 0
    for p in targets:
        freed += dir_size(p)
        try:
            shutil.rmtree(p)
            removed += 1
        except FileNotFoundError:
            pass
    return (removed, freed)


def cache_statistics(root: Path | None = None) -> dict:
    entries = scan_cache(root)
    unique_videos = len({e.video_id for e in entries})
    return {
        "entries": len(entries),
        "unique_videos": unique_videos,
        "total_size_bytes": sum(e.size_bytes for e in entries),
    }


def expire_cache(ttl_seconds: int, root: Path | None = None) -> list[Path]:
    """Delete artifact dirs whose created_at exceeds TTL.

    Returns list of removed directories. Only considers entries with valid created_at.
    """
    now = datetime.now(timezone.utc)
    removed: list[Path] = []
    for e in scan_cache(root):
        if e.created_at is None:
            continue
        created = e.created_at.astimezone(timezone.utc)
        age = (now - created).total_seconds()
        if age > ttl_seconds:
            try:
                shutil.rmtree(e.dir)
                removed.append(e.dir)
            except FileNotFoundError:
                pass
    return removed


def get_ttl_seconds_from_env() -> int | None:
    """Read TTL from env: YTX_CACHE_TTL_SECONDS or YTX_CACHE_TTL_DAYS."""
    s = os.environ.get("YTX_CACHE_TTL_SECONDS")
    if s:
        try:
            v = int(s)
            return v if v > 0 else None
        except Exception:
            return None
    d = os.environ.get("YTX_CACHE_TTL_DAYS")
    if d:
        try:
            v = int(d)
            return v * 86400 if v > 0 else None
        except Exception:
            return None
    return None


__all__ = [
    "META_JSON",
    "TRANSCRIPT_JSON",
    "CAPTIONS_SRT",
    "SUMMARY_JSON",
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
    "read_summary",
    "write_summary",
    "write_bytes_atomic",
    "build_meta_payload",
    "write_meta",
    "CacheEntry",
    "scan_cache",
    "clear_cache",
    "cache_statistics",
    "expire_cache",
    "get_ttl_seconds_from_env",
]
