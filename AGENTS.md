# Repository Guidelines

## Project Structure & Module Organization
This repo hosts a uv project under `ytx/` using the src layout:
- Code: `ytx/src/ytx/` (package root with modules like `cli.py`, `config.py`, `models.py`).
- Tests: `ytx/tests/` (unit and light e2e).
- Docs: `IMP.md`, `Phase1.md`, `AGENTS.md` in repo root.
- Working dirs (gitignored during development): `data/`, `artifacts/`.
See IMP.md for the planned module breakdown (exporters, engines, downloader, audio, cache).

## Build, Test, and Development Commands
- Change into project dir: `cd ytx`
- Install deps: `uv sync`
- Run CLI help: `uv run ytx --help`
- Transcribe (local): `uv run ytx transcribe <url> --engine whisper --model small`
- Transcribe (Gemini): `GEMINI_API_KEY=... uv run ytx transcribe <url> --engine gemini`
- Tests: `uv run pytest -q`
- Lint (if added): `uv run ruff check .` and format `uv run ruff format .`

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
