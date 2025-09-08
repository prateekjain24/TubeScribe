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
