from __future__ import annotations

"""Central error types and helpers (Sprint 11: ERROR-001).

Provides a base error with a stable `code` and friendly string formatting,
plus common subclasses for network, API, filesystem, timeout, and more.
"""

from dataclasses import dataclass
from typing import Any


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
]

