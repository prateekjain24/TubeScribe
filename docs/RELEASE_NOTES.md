TubeScribe Release Notes
========================

v0.2.1 (2025-09-08)
--------------------
- Packaging: renamed distribution to `tubescribe` (keeps CLI alias `ytx`).
- CLI: both `ytx` and `tubescribe` entry points installed.
- Version detection: CLI now resolves version from `tubescribe` or `ytx` dists.
- Metadata: added long description, classifiers, keywords, optional extras.
- Wheel build: fixed package inclusion for `src/ytx/` in wheels.
- Licensing: added MIT LICENSE file.
- Publishing: uploaded to TestPyPI and PyPI.

Install
- `pip install tubescribe`
- Run: `ytx --version` or `tubescribe --version`

Notes
- FFmpeg required on PATH for audio processing.
- Optional: set `GEMINI_API_KEY`/`GOOGLE_API_KEY` for summaries.

v0.2.2 (2025-09-08)
--------------------
- CLI health: add checks for `whisper_engine` (faster-whisper), `whispercpp_bin` presence, `yt-dlp`, and cloud provider keys (`OPENAI_API_KEY`, `DEEPGRAM_API_KEY`).
- README: add Health Reference; make badges clickable; add downloads badge.

v0.2.3 (2025-09-08)
--------------------
- Gemini (chunked): fix pydantic assignment error when offsetting chunked segments by constructing new TranscriptSegment instances instead of mutating in place.

v0.2.4 (2025-09-08)
--------------------
- OpenAI/Deepgram (chunked): apply the same safe offset strategy (no in-place mutation) to prevent end<=start validation errors at chunk boundaries.

v0.3.0 (2025-09-08)
--------------------
- New: MarkdownExporter (`md`) to generate notes-ready Markdown files.
  - Title with YouTube link, optional YAML frontmatter for Obsidian.
  - Summary TL;DR + key bullets (when present).
  - Chapter outline with clickable timestamps.
  - Optional transcript section (off by default).
- CLI: `ytx export` command to export from cache (`--video-id`) or from a TranscriptDoc JSON file (`--from-file`).
- Docs: README and API updated with usage and options.

v0.3.2 (2025-09-08)
--------------------
- fix(cache): `scan_cache` and artifact checks now accept legacy `<video_id>.json/.srt` alongside canonical `transcript.json/captions.srt`.
- fix(cli:export): when `transcript.json` is missing, fall back to `<video_id>.json` for cached export.

v0.3.3 (2025-09-08)
--------------------
- fix(cache): correct cache directory parsing (`<root>/<video>/<engine>/<model>/<hash>`) when deriving `video_id`, ensuring cache listings and exports find entries.
- test(cache): add test to validate video_id parsing and cache scanning.

v0.3.4 (2025-09-08)
--------------------
- feat(export-md): auto-chapters synthesis when missing (`--md-auto-chapters-min N`), generating a chapter outline at fixed intervals.
- docs: README updated with auto-chapters option.
