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

