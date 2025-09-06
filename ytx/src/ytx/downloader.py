from __future__ import annotations

"""Downloader module skeleton.

DOWNLOAD-001 scope: create structure and configure logging with Rich.
Actual metadata fetching via yt-dlp is implemented in DOWNLOAD-002.
"""

import logging
import re
from typing import Final

from rich.logging import RichHandler

from .models import VideoMetadata


# Configure module logger with Rich handler (idempotent)
_LOGGER_NAME: Final[str] = "ytx.downloader"
logger = logging.getLogger(_LOGGER_NAME)
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="%H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True, show_time=False, show_path=False)],
    )
    # Avoid duplicated logs if root is configured elsewhere
    logger.propagate = False


_YOUTUBE_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|live/|shorts/)|youtu\.be/)[A-Za-z0-9_-]{6,}$",
    re.IGNORECASE,
)


def is_youtube_url(url: str) -> bool:
    """Lightweight YouTube URL format check (supports youtu.be and youtube.com)."""
    return bool(_YOUTUBE_RE.match(url.strip()))


class YTDLPError(RuntimeError):
    """Raised when yt-dlp operations fail (populated in DOWNLOAD-002)."""


def fetch_metadata(url: str) -> VideoMetadata:  # noqa: D401
    """Fetch video metadata via yt-dlp (to be implemented in DOWNLOAD-002)."""
    raise NotImplementedError("DOWNLOAD-002 implements yt-dlp metadata fetching")

