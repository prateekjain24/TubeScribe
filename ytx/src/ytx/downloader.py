from __future__ import annotations

"""Downloader module skeleton.

DOWNLOAD-001 scope: create structure and configure logging with Rich.
Actual metadata fetching via yt-dlp is implemented in DOWNLOAD-002.
"""

import logging
import re
from pathlib import Path
from typing import Final, Any

from rich.logging import RichHandler

from .models import VideoMetadata
from .chapters import parse_yt_dlp_chapters
from .audio import ensure_ffmpeg
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_random_exponential


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


_YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_HOST_RE = re.compile(r"^(?:.+\.)?(youtube\.com|youtu\.be|youtube-nocookie\.com)$", re.I)


def extract_video_id(url: str) -> str | None:
    """Extract the 11-char YouTube video ID from common URL shapes.

    Supports:
    - https://www.youtube.com/watch?v=VIDEOID
    - https://youtu.be/VIDEOID
    - https://www.youtube.com/shorts/VIDEOID
    - https://www.youtube.com/live/VIDEOID
    - https://www.youtube.com/embed/VIDEOID
    - music.youtube.com/watch?v=VIDEOID
    Ignores extra params like `t=`, `si=`, `feature=`.
    """
    from urllib.parse import urlparse, parse_qs

    s = url.strip()
    if not s:
        return None
    # Handle bare IDs passed by user
    if _YT_ID_RE.match(s):
        return s

    parsed = urlparse(s)
    host = (parsed.netloc or "").lower()
    host = host.split(":")[0]
    if not _HOST_RE.match(host):
        return None

    path = parsed.path or ""
    # youtu.be/<id>
    if host.endswith("youtu.be"):
        parts = [p for p in path.split("/") if p]
        if parts:
            candidate = parts[0]
            return candidate if _YT_ID_RE.match(candidate) else None

    # youtube.com/watch?v=<id>
    qs = parse_qs(parsed.query)
    v = qs.get("v", [None])[0]
    if v and _YT_ID_RE.match(v):
        return v

    # youtube.com/shorts/<id>, /live/<id>, /embed/<id>
    parts = [p for p in path.split("/") if p]
    if parts:
        if parts[0] in {"shorts", "live", "embed"} and len(parts) >= 2:
            candidate = parts[1]
            return candidate if _YT_ID_RE.match(candidate) else None

    return None


def is_youtube_url(url: str) -> bool:
    """Return True if URL appears to reference a specific YouTube video."""
    return extract_video_id(url) is not None


def canonical_url(video_id: str) -> str:
    """Return a canonical short URL for the given video id."""
    if not _YT_ID_RE.match(video_id):
        raise ValueError("Invalid YouTube video id")
    return f"https://youtu.be/{video_id}"


from .errors import ExternalToolError


class YTDLPError(ExternalToolError):
    """Raised when yt-dlp operations fail (populated in DOWNLOAD-002)."""


def _format_selector(max_abr_kbps: int | None) -> str:
    """Return yt-dlp format selector honoring an optional abr cap.

    96 -> "bestaudio[abr<=96]/bestaudio"; None/0 -> "bestaudio/best".
    """
    try:
        v = int(max_abr_kbps) if max_abr_kbps is not None else 0
    except Exception:
        v = 0
    return f"bestaudio[abr<={v}]/bestaudio" if v > 0 else "bestaudio/best"


def _build_yt_dlp_cmd(
    url: str,
    *,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    quiet: bool = True,
    max_abr_kbps: int | None = None,
) -> list[str]:
    cmd: list[str] = [
        "yt-dlp",
        "--no-playlist",
        "--no-download",
        "-f",
        _format_selector(max_abr_kbps),
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
    # Extract duration for chapter end inference
    duration = data.get("duration")
    try:
        vd = float(duration) if duration is not None else None
    except Exception:
        vd = None
    chapters = parse_yt_dlp_chapters(data, video_duration=vd)
    return VideoMetadata(
        id=str(data.get("id") or ""),
        title=data.get("title"),
        duration=data.get("duration"),
        url=str(data.get("webpage_url") or data.get("original_url") or fallback_url),
        uploader=data.get("uploader"),
        description=data.get("description"),
        chapters=chapters or None,
    )


def fetch_metadata(
    url: str,
    *,
    timeout: int = 90,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    max_abr_kbps: int | None = None,
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
        max_abr_kbps=max_abr_kbps,
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
        from .errors import TimeoutError

        raise TimeoutError(f"yt-dlp timed out after {timeout}s")

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        msg = _friendly_yt_dlp_error(stderr, url)
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


def download_audio(
    meta: VideoMetadata,
    out_dir: Path,
    *,
    audio_format: str = "m4a",
    audio_quality: str = "0",
    overwrite: bool = False,
    timeout: int = 60 * 30,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    use_api: bool = True,
    max_abr_kbps: int | None = None,
) -> Path:
    """Download best audio and extract to requested format.

    Returns the path to the extracted audio file (e.g. <out_dir>/<id>.m4a).
    """
    import shutil
    import subprocess

    if not shutil.which("yt-dlp"):
        raise YTDLPError("yt-dlp is not installed or not on PATH")
    ensure_ffmpeg()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    expected = out_dir / f"{meta.id}.{audio_format}"
    if expected.exists() and not overwrite and _is_nonempty_file(expected):
        logger.info("Audio exists and is non-empty, skipping: %s", expected)
        return expected

    # Retry wrapper: attempt up to 3 times on YTDLPError with exponential backoff (jitter)
    for attempt in Retrying(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, max=8),
        retry=retry_if_exception_type(YTDLPError),
        reraise=True,
    ):
        with attempt:
            path = _download_audio_once(
                meta,
                out_dir,
                expected,
                timeout=timeout,
                audio_format=audio_format,
                audio_quality=audio_quality,
                overwrite=overwrite,
                cookies_from_browser=cookies_from_browser,
                cookies_file=cookies_file,
                use_api=use_api,
                max_abr_kbps=max_abr_kbps,
            )
            if not _is_nonempty_file(path):
                raise YTDLPError(f"download produced empty file: {path}")
            return path

    # Should not reach here because reraise=True will raise on final failure
    raise YTDLPError("download failed after retries")


def _is_nonempty_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except FileNotFoundError:
        return False


def _download_audio_once(
    meta: VideoMetadata,
    out_dir: Path,
    expected: Path,
    *,
    timeout: int,
    audio_format: str,
    audio_quality: str,
    overwrite: bool,
    cookies_from_browser: str | None,
    cookies_file: str | None,
    use_api: bool,
    max_abr_kbps: int | None,
) -> Path:
    if use_api:
        try:
            return _download_audio_api(
                meta,
                out_dir,
                audio_format=audio_format,
                audio_quality=audio_quality,
                overwrite=overwrite,
                cookies_from_browser=cookies_from_browser,
                cookies_file=cookies_file,
                max_abr_kbps=max_abr_kbps,
            )
        except Exception as e:  # fallback to subprocess for resilience
            logger.warning("yt-dlp API failed (%s); falling back to subprocess", e)

    # Fallback: Use yt-dlp CLI to extract bestaudio and convert to target format via ffmpeg
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f",
        _format_selector(max_abr_kbps),
        "--extract-audio",
        "--audio-format",
        audio_format,
        "--audio-quality",
        audio_quality,
        "--continue",
        "--no-part",
        "--no-mtime",
        "-o",
        str(out_dir / "%(id)s.%(ext)s"),
        meta.url,
    ]
    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    if cookies_file:
        cmd.extend(["--cookies", cookies_file])

    logger.info("Downloading audio for %s → %s", meta.id, expected.name)
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        from .errors import TimeoutError

        raise TimeoutError(f"yt-dlp download timed out after {timeout}s")

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise YTDLPError(_friendly_yt_dlp_error(stderr, meta.url))

    # Validate expected output exists or guess by id
    if expected.exists():
        return expected
    for p in out_dir.glob(f"{meta.id}.*"):
        if p.is_file():
            return p
    raise YTDLPError(f"expected audio file not found: {expected}")


def _friendly_yt_dlp_error(stderr: str, url: str) -> str:
    """Return a concise, actionable error message for common yt-dlp failures."""
    s = stderr.lower()
    hint = None

    def suggest_cookies() -> str:
        return (
            "Restricted content detected. Try cookies: "
            "cookies_from_browser='chrome' or cookies_file='cookies.txt'"
        )

    if any(x in s for x in ["age-restricted", "confirm your age", "sign in to confirm"]):
        hint = suggest_cookies()
    elif "not available in your country" in s or "blocked in your country" in s:
        hint = suggest_cookies() + "; region restrictions may apply"
    elif "private video" in s or "this video is private" in s:
        hint = "Video is private; access requires appropriate account permissions"
    elif "members-only" in s or "premium" in s:
        hint = "Members-only or Premium content; requires an authorized account"
    elif "live" in s and ("ended" in s or "finished" in s):
        hint = "Live event ended; VOD may not be available yet"

    base = "yt-dlp failed"
    tail = " | ".join(stderr.strip().splitlines()[-5:]) if stderr.strip() else ""
    if hint:
        return f"{base}: {tail} | {hint}"
    return f"{base}: {tail}"


def _download_audio_api(
    meta: VideoMetadata,
    out_dir: Path,
    *,
    audio_format: str,
    audio_quality: str,
    overwrite: bool,
    cookies_from_browser: str | None,
    cookies_file: str | None,
    max_abr_kbps: int | None,
) -> Path:
    """Download audio using yt-dlp's Python API with a Rich progress bar."""
    from rich.progress import Progress, BarColumn, TimeRemainingColumn, DownloadColumn, TransferSpeedColumn, TextColumn

    # Defer import to runtime to keep module load light
    try:
        from yt_dlp import YoutubeDL  # type: ignore
    except Exception as e:  # pragma: no cover
        raise YTDLPError(f"yt-dlp import failed: {e}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    expected = out_dir / f"{meta.id}.{audio_format}"
    if expected.exists() and not overwrite:
        logger.info("Audio exists, skipping download: %s", expected)
        return expected

    task_id: int | None = None
    total: int | None = None

    def hook(d: dict[str, Any]) -> None:
        nonlocal task_id, total
        status = d.get("status")
        if status == "downloading":
            downloaded = int(d.get("downloaded_bytes") or 0)
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total_bytes and total_bytes != total:
                total = int(total_bytes)
                if task_id is not None:
                    progress.update(task_id, total=total)
            if task_id is None:
                task_id = progress.add_task(f"Downloading {meta.id}", total=total or 0)
            progress.update(task_id, completed=downloaded)
        elif status == "finished":
            if task_id is not None:
                progress.update(task_id, completed=total or progress.tasks[task_id].completed)

    ydl_opts: dict[str, Any] = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "continuedl": True,
        "nopart": True,
        "no_mtime": True,
        "overwrites": bool(overwrite),
        "format": _format_selector(max_abr_kbps),
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "progress_hooks": [hook],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": audio_quality,
            }
        ],
    }
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = cookies_from_browser
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file

    logger.info("Downloading audio for %s → %s", meta.id, expected.name)
    with Progress(
        TextColumn("{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([meta.url])

    if not expected.exists():
        # Attempt to find the file by id with any extension (rare mismatch)
        for p in out_dir.glob(f"{meta.id}.*"):
            if p.is_file():
                return p
        raise YTDLPError(f"expected audio file not found: {expected}")

    return expected
