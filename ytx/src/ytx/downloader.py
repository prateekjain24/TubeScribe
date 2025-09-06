from __future__ import annotations

"""Downloader module skeleton.

DOWNLOAD-001 scope: create structure and configure logging with Rich.
Actual metadata fetching via yt-dlp is implemented in DOWNLOAD-002.
"""

import logging
import re
from typing import Final, Any

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


def _build_yt_dlp_cmd(
    url: str,
    *,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    quiet: bool = True,
) -> list[str]:
    cmd: list[str] = [
        "yt-dlp",
        "--no-playlist",
        "--no-download",
        "--dump-json",
        "--no-warnings",
    ]
    if quiet:
        cmd.extend(["-q"])
    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    if cookies_file:
        cmd.extend(["--cookies", cookies_file])
    cmd.append(url)
    return cmd


def _parse_metadata(data: dict[str, Any], fallback_url: str) -> VideoMetadata:
    return VideoMetadata(
        id=str(data.get("id") or ""),
        title=data.get("title"),
        duration=data.get("duration"),
        url=str(data.get("webpage_url") or data.get("original_url") or fallback_url),
        uploader=data.get("uploader"),
        description=data.get("description"),
    )


def fetch_metadata(
    url: str,
    *,
    timeout: int = 90,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> VideoMetadata:
    """Fetch video metadata using yt-dlp --dump-json.

    This function performs a single-video metadata fetch (no playlists) and returns
    a normalized VideoMetadata model. For age/region-restricted videos, provide
    `cookies_from_browser` (e.g., "chrome") or a `cookies_file` path.
    """
    import json
    import shutil
    import subprocess

    if not shutil.which("yt-dlp"):
        raise YTDLPError("yt-dlp is not installed or not on PATH")

    cmd = _build_yt_dlp_cmd(
        url,
        cookies_from_browser=cookies_from_browser,
        cookies_file=cookies_file,
        quiet=True,
    )
    logger.debug("Running yt-dlp: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise YTDLPError(f"yt-dlp timed out after {timeout}s") from e

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip().splitlines()[-5:]
        msg = "yt-dlp failed (code %s): %s" % (proc.returncode, " | ".join(stderr_tail))
        raise YTDLPError(msg)

    stdout = (proc.stdout or "").strip()
    if not stdout:
        raise YTDLPError("yt-dlp produced no output")

    # --dump-json emits one JSON object. Parse directly.
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        # Some variants may emit multiple JSON objects (rare with --no-playlist).
        # Fall back to last valid JSON object per line.
        meta: dict[str, Any] | None = None
        for line in stdout.splitlines():
            try:
                meta = json.loads(line)
            except json.JSONDecodeError:
                continue
        if not meta:
            raise YTDLPError("Failed to parse yt-dlp JSON output") from e
        data = meta

    vm = _parse_metadata(data, fallback_url=url)
    if not vm.id:
        raise YTDLPError("Missing video id in yt-dlp output")
    logger.info("Fetched metadata: id=%s title=%s", vm.id, (vm.title or ""))
    return vm
