from __future__ import annotations

"""Central error types and helpers (Sprint 11: ERROR-001).

Provides a base error with a stable `code` and friendly string formatting,
plus common subclasses for network, API, filesystem, timeout, and more.
"""

from dataclasses import dataclass
from typing import Any
from pathlib import Path
from datetime import datetime, timezone
import os
import platform
import traceback

try:
    import orjson as _orjson  # type: ignore

    def _dumps(obj: Any) -> bytes:
        return _orjson.dumps(obj, option=_orjson.OPT_SORT_KEYS)
except Exception:  # pragma: no cover
    import json as _json

    def _dumps(obj: Any) -> bytes:  # type: ignore[no-redef]
        return _json.dumps(obj, sort_keys=True, indent=2).encode("utf-8")


@dataclass
class YTXError(Exception):
    code: str
    message: str
    cause: Exception | None = None
    context: dict[str, Any] | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        base = f"[{self.code}] {self.message}"
        if self.context:
            try:
                extras = ", ".join(f"{k}={v}" for k, v in self.context.items())
                base += f" ({extras})"
            except Exception:
                pass
        return base


class InvalidInputError(YTXError):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None):
        super().__init__(code="INPUT", message=message, context=context)


class FileSystemError(YTXError):
    def __init__(self, message: str, *, cause: Exception | None = None, context: dict[str, Any] | None = None):
        super().__init__(code="FILESYSTEM", message=message, cause=cause, context=context)


class ExternalToolError(YTXError):
    def __init__(self, message: str, *, cause: Exception | None = None, context: dict[str, Any] | None = None):
        super().__init__(code="EXTERNAL", message=message, cause=cause, context=context)


class NetworkError(YTXError):
    def __init__(self, message: str, *, cause: Exception | None = None, context: dict[str, Any] | None = None):
        super().__init__(code="NETWORK", message=message, cause=cause, context=context)


class APIError(YTXError):
    def __init__(self, message: str, *, provider: str | None = None, cause: Exception | None = None, context: dict[str, Any] | None = None):
        ctx = dict(context or {})
        if provider:
            ctx.setdefault("provider", provider)
        super().__init__(code="API", message=message, cause=cause, context=ctx)


class RateLimitError(APIError):
    def __init__(self, message: str = "Rate limit exceeded", *, provider: str | None = None, cause: Exception | None = None, context: dict[str, Any] | None = None):
        super().__init__(message, provider=provider, cause=cause, context=context)
        self.code = "RATE_LIMIT"


class TimeoutError(YTXError):
    def __init__(self, message: str = "Operation timed out", *, cause: Exception | None = None, context: dict[str, Any] | None = None):
        super().__init__(code="TIMEOUT", message=message, cause=cause, context=context)


class InterruptError(YTXError):
    def __init__(self, message: str = "Operation interrupted", *, context: dict[str, Any] | None = None):
        super().__init__(code="INTERRUPT", message=message, context=context)


class HealthCheckError(YTXError):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None):
        super().__init__(code="HEALTH", message=message, context=context)


def friendly_error(e: Exception) -> str:  # pragma: no cover - trivial formatting
    if isinstance(e, YTXError):
        return str(e)
    return f"[UNKNOWN] {e}"


def _sanitize_env(env: dict[str, str]) -> dict[str, str]:
    redact = ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH", "COOKIE")
    out: dict[str, str] = {}
    for k, v in env.items():
        uk = k.upper()
        if any(r in uk for r in redact):
            continue
        if len(v) > 256:
            out[k] = v[:256] + "…"
        else:
            out[k] = v
    return out


def write_error_report(dir_path: Path, exc: Exception, *, context: dict[str, Any] | None = None) -> Path:
    """Write a sanitized error report JSON and return its path (ERROR-008).

    The report includes timestamp, error code/message (if YTXError), traceback,
    environment (sanitized), platform info, and optional context.
    """
    dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = dir_path / f"error_{ts}.json"
    err: dict[str, Any] = {
        "timestamp": ts,
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
        "platform": {
            "python": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "env": _sanitize_env(dict(os.environ)),
        "context": context or {},
    }
    if isinstance(exc, YTXError):
        err["code"] = exc.code
        if exc.context:
            err["context"].update(exc.context)
    try:
        data = _dumps(err)
        # lazy import to avoid cycles
        from .cache import write_bytes_atomic  # type: ignore

        write_bytes_atomic(path, data)
    except Exception:
        # best-effort fallback
        path.write_bytes(data if isinstance(data, (bytes, bytearray)) else bytes(data))  # type: ignore[arg-type]
    return path


__all__ = [
    "YTXError",
    "InvalidInputError",
    "FileSystemError",
    "ExternalToolError",
    "NetworkError",
    "APIError",
    "RateLimitError",
    "TimeoutError",
    "InterruptError",
    "HealthCheckError",
    "friendly_error",
    "write_error_report",
]
