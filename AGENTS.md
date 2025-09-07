# Repository Guidelines

## Project Structure & Module Organization
This repo hosts a uv project under `ytx/` using the src layout:
- Code: `ytx/src/ytx/` (package root with modules like `cli.py`, `config.py`, `models.py`).
- Tests: `ytx/tests/` (unit and light e2e).
- Docs: `IMP.md`, `Phase1.md`, `AGENTS.md` in repo root.
- Working dirs (gitignored during development): `data/`, `artifacts/`.
See IMP.md for the planned module breakdown (exporters, engines, downloader, audio, cache).

## Build, Test, and Development Commands
- Option A (recommended): venv + pip
  - `cd ytx && python3.11 -m venv .venv && source .venv/bin/activate`
  - `python -m pip install -U pip setuptools wheel && python -m pip install -e .`
  - `ytx --help`
- Option B: uv
  - `cd ytx && uv sync`
  - `uv run ytx --help`
- Run without installing (module form):
  - From repo root: `export PYTHONPATH="$(pwd)/ytx/src" && cd ytx && python3 -m ytx.cli --help`
- Common commands:
  - Transcribe (Whisper): `ytx transcribe <url> --engine whisper --model small`
  - Transcribe (Gemini): `ytx transcribe <url> --engine gemini --timestamps chunked --fallback`
  - Chapters + summaries: `ytx transcribe <url> --by-chapter --parallel-chapters --summarize-chapters --summarize`
  - Health check: `ytx health`
  - Summarize existing transcript: `ytx summarize-file /path/to/<id>.json --write`
  - Cache: `ytx cache ls | ytx cache stats | ytx cache clear --yes [--video-id <id>]`
 - Tests/Lint (if configured): `pytest -q`, `ruff check .`

## Coding Style & Naming Conventions
- Python 3.11+, PEP 8, 4‑space indent, type hints required on public functions.
- Naming: modules/files `snake_case.py`, functions/vars `snake_case`, classes `CamelCase`.
- Prefer small, single‑purpose modules; keep functions under ~50–80 lines when feasible.
- Logging via `ytx.logging` (Rich); avoid `print()` in library code.

## Testing Guidelines
- Framework: `pytest` with unit tests under `tests/`, files named `test_*.py`.
- Focus areas: exporters (SRT/VTT), chunking/stitching, config hashing, downloader metadata parse.
- Cloud path should auto‑skip when `GEMINI_API_KEY` is absent; keep offline tests default.
- Add fixtures for tiny audio clips; avoid network in unit tests.

## Commit & Pull Request Guidelines
- Use Conventional Commits style: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`.
  - Example: `feat(cli): add --chapters flag with stitching`
- PRs must include: problem summary, what changed, test coverage summary, and sample command output (e.g., SRT lines count).
- Keep PRs scoped; prefer incremental changes. Link issues when applicable.

## Security & Configuration Tips
- Never commit secrets or cookies; use `.env` locally and `GEMINI_API_KEY` env var.
- System deps: ensure `ffmpeg` is installed and on PATH.
- yt‑dlp: for age/region restricted videos, prefer `--cookies-from-browser` locally; do not add cookies to the repo.

## Progress & Notes (ongoing)
- Caching: XDG-aware cache, artifact paths, existence checks, atomic writes, `meta.json` + `summary.json`, list/clear/stats/expiration.
- Downloader: robust URL parsing, metadata via yt‑dlp, resilient download (API + subprocess), retries, friendly errors.
- Audio: ffmpeg normalization (16 kHz mono WAV), ffprobe duration, ffmpeg slicing for chapters/chunks.
- Exporters: JSON (deterministic) and SRT (wrapped); manager utilities.
- Engines:
  - Whisper (faster‑whisper): device/compute auto, model cache, transcription, optional language detect.
  - Gemini: API key loading, model setup, chunking + stitching, best‑effort timestamps, retries with backoff, fallback to Whisper.
- Chapters: parse from yt‑dlp; slice per chapter; parallel processing; offset and stitch; optional per‑chapter summaries.
- Summaries: transcript‑level TL;DR + bullets with hierarchical summarization; cached to `summary.json`.
- Errors & health: central error types, timeouts, error reports (sanitized), health checks, graceful interrupts, partial save.

## Key Learnings & Gotchas
- uv lockfile: uv uses a workspace lock at `~/uv.lock` when a higher‑level workspace exists; we keep Option A (workspace lock) for now.
- Typer extras: `typer[all]` is not available on newer Typer; depend on `typer` only. `pretty_exceptions_enable` can be disabled at app init.
- faster‑whisper: CTranslate2 devices are `cpu|cuda|auto`; map `metal`→`cpu`. Default model set to `large-v3-turbo` (configurable).
- yt‑dlp API vs CLI: prefer API for progress; fallback to CLI for resilience. Ensure `ffmpeg` exists before downloads/extracts.
- Registry warm‑up: exporter manager lazily imports built‑ins to populate the registry before parsing format specs.
- Avoid committing ad‑hoc artifacts (e.g., generated `.json/.srt`) to repo; keep outputs under a cache/artifacts dir.
 - Namespace shadowing: when inside the `ytx/` folder, `import ytx` may resolve to the folder, not the installed package. Prefer `python -m ytx.cli …` or run console scripts from repo root.
