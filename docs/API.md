# ytx API and CLI Overview

This document outlines the primary CLI commands and the internal Python
modules most users and contributors will interact with.

## CLI Commands

- `ytx transcribe <url>`: End‑to‑end pipeline.
  - Common options:
    - `--engine {whisper,whispercpp,gemini}`
    - `--model <name>` (e.g., `small`, `large-v3-turbo`, or `gemini-2.5-flash`)
    - `--timestamps {native,chunked,none}`
    - `--by-chapter` `--parallel-chapters/--no-parallel-chapters` `--chapter-overlap <sec>`
    - `--summarize` (overall TL;DR + bullets), `--summarize-chapters` (per chapter)
    - `--engine-opts '{"utterances":true}'` (provider‑specific options)
    - `--output-dir <dir>`, `--overwrite`
  - Cache behavior: artifacts are written to XDG cache under
    `<video_id>/<engine>/<model>/<config_hash>/`.

- `ytx summarize-file <transcript.json> [--write]`:
  - Reads a TranscriptDoc JSON and generates a TL;DR + key bullets.
  - Writes `<video_id>.summary.json` when `--write` is provided.

- `ytx health`: Checks ffmpeg availability, Gemini key presence, and basic network.

- `ytx cache ls|stats|clear`: List, inspect, and clear cache entries.

## Programmatic Modules (selected)

- `ytx.downloader`:
  - `extract_video_id(url: str) -> str | None`
  - `fetch_metadata(url: str, *, timeout: int) -> VideoMetadata`
  - `download_audio(meta: VideoMetadata, out_dir: Path, *, timeout: int, ...) -> Path`

- `ytx.audio`:
  - `normalize_wav(src: Path, dst: Path, *, overwrite: bool=False) -> Path`
  - `probe_duration(path: Path) -> float`

- `ytx.cache`:
  - Paths: `build_artifact_paths(...) -> ArtifactPaths`
  - Checks: `artifacts_exist(paths) -> bool`
  - IO: `write_meta(paths, payload)`, `read_meta(paths)`, `write_summary(paths, payload)`, `read_summary(paths)`

- `ytx.engines`:
  - Protocol: `TranscriptionEngine.transcribe(audio_path, *, config, on_progress=None) -> list[TranscriptSegment]`
  - Engines: `WhisperEngine`, `GeminiEngine` (with backoff & chunking), `WhisperCppEngine` (optional)

- `ytx.chapters`:
  - `parse_yt_dlp_chapters(meta, *, video_duration) -> list[Chapter]`
  - `slice_audio_by_chapters(...) -> list[(idx, Chapter, Path)]`
  - `process_chapters(...) -> list[(idx, Chapter, list[TranscriptSegment])]`
  - `offset_chapter_segments(...) -> list[TranscriptSegment]`
  - `stitch_chapter_segments(...) -> list[TranscriptSegment]`

- `ytx.exporters`:
  - `JSONExporter`, `SRTExporter`, `MarkdownExporter` (name: `md`)
  - Manager: `export_all(doc, out_dir, formats)` and `parse_formats("json,srt,md")`
  - CLI: `ytx export --video-id <id> --to md --output-dir ./notes` writes `<id>.md` with optional frontmatter, summary, bullets, and chapter links.

- `ytx.config`:
  - `AppConfig`: engine/model/language/device/compute_type
  - Cross‑provider: `timestamp_policy`, `engine_options`, timeouts.
  - `config_hash()` returns a deterministic hash for caching.

- `ytx.errors`:
  - `YTXError` base + `APIError`, `RateLimitError`, `FileSystemError`, `TimeoutError`, etc.
  - `write_error_report(dir, exc, context=...)` to generate a sanitized error report.

## Models

- Transcript: `TranscriptDoc` with `segments: list[TranscriptSegment]`, optional
  `chapters: list[Chapter]` and `summary` (`{tldr, bullets[]}`).

- Video metadata: `VideoMetadata` derived from yt‑dlp `--dump-json`.

## Extension Points

- Engines: add a new engine class implementing `TranscriptionEngine`, register
  with `@register_engine`, and support `engine_options` as needed.

- Exporters: implement `FileExporter` and decorate with `@register_exporter`.
