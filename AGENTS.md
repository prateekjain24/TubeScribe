# TubeScribe (ytx) — Engineering Guide

This document orients contributors to the code layout, workflows, and practical tips for working on TubeScribe. The package is published to PyPI as `tubescribe`, with console commands `ytx` and `tubescribe`.

## Project Structure
- Code: `ytx/src/ytx/`
  - CLI: `cli.py`
  - Engines: `engines/` (whisper, whispercpp, gemini, openai, deepgram, elevenlabs stub)
  - Exporters: `exporters/` (JSON, SRT, manager)
  - Core modules: `audio.py`, `downloader.py`, `cache.py`, `chapters.py`, `models.py`, `stitch.py`, `logging.py`, `config.py`
  - Summarization: `summarizer.py` (Gemini)
- Tests: `ytx/tests/` (unit + light integration)
- Docs: `docs/` (API/CONFIG/RELEASE notes and GitHub release bodies)
- Packaging: `ytx/pyproject.toml` (dist name `tubescribe`)

## Install & Dev
- CLI (recommended): `pipx install tubescribe` (or `pip install tubescribe`)
  - Verify: `ytx --version` or `tubescribe --version`
- Dev (editable):
  - `cd ytx && python3.11 -m venv .venv && source .venv/bin/activate`
  - `python -m pip install -U pip && python -m pip install -e .`
  - Run without install: `export PYTHONPATH="$(pwd)/ytx/src" && cd ytx && python -m ytx.cli --help`

## Common CLI
- Health: `ytx health`
- Transcribe (Whisper): `ytx transcribe <url> --engine whisper --model small`
- Transcribe (Gemini): `ytx transcribe <url> --engine gemini --timestamps chunked --fallback`
- Per‑chapter + summaries: `ytx transcribe <url> --by-chapter --parallel-chapters --chapter-overlap 2.0 --summarize --summarize-chapters`
- Summarize existing JSON: `ytx summarize-file /path/to/<video_id>.json --write`
- Cache: `ytx cache ls | ytx cache stats | ytx cache clear --yes [--video-id <id>]`

Tip (zsh): keep long commands on one line or use trailing `\` to avoid “command not found” for wrapped flags.

## Feature Overview (0.3.x)
- Markdown Export (md): notes‑ready output with optional YAML frontmatter, TL;DR + bullets, chapter outline with clickable timestamps; optional transcript section.
- CLI Export: `ytx export --video-id <id> --to md --output-dir ./notes` or `--from-file <doc.json>`.
- Auto‑Chapters: synthesize chapters when none exist via `--md-auto-chapters-min N`.
- Cache Compatibility: honors both canonical names (`transcript.json`, `captions.srt`) and legacy names (`<video_id>.json/.srt`).
- Health: ffmpeg, whisper engine import, whisper.cpp binary presence, yt‑dlp, and cloud key checks.

## Caching & Artifacts
- Root: `~/.cache/ytx` (override with `YTX_CACHE_DIR`)
- Layout: `<video_id>/<engine>/<model>/<config_hash>/`
- Files: `transcript.json`, `captions.srt`, `meta.json`, `summary.json` (if generated), plus intermediate audio.
- Legacy names supported: `<video_id>.json`, `<video_id>.srt` are recognized for export/listing.
- `--output-dir` also writes JSON/SRT to a chosen folder (summary remains in cache).

## Engines
- Whisper (faster‑whisper): local transcription. Device auto map (`metal`→`cpu`), model cache, optional language detect.
- whisper.cpp (Metal): requires a gguf model and binary (`main`); set `YTX_WHISPERCPP_BIN` and `YTX_WHISPERCPP_MODEL_PATH`.
- Gemini: cloud LLM transcription with chunking + stitching; good with `--timestamps chunked` and `--fallback`.
- OpenAI: SDK‑first optional, HTTP fallback; parses verbose JSON when available; supports chunked stitching.
- Deepgram: SDK‑first optional, HTTP fallback; good defaults (`utterances`, `smart_format`); supports chunked stitching.
- ElevenLabs: stub placeholder for future STT.

Chunked safety: for cloud engines we construct new segments when offsetting to avoid Pydantic assignment errors; tests guard `end > start` across chunk boundaries.

## Summaries
- Overall: `--summarize` adds `summary` to transcript.json and writes `summary.json` in cache.
- Per‑chapter: `--summarize-chapters` fills `chapters[].summary` either from chapter slices or from global segments.
- Requires `GEMINI_API_KEY` (or `GOOGLE_API_KEY`).

## Health & Troubleshooting
- `ytx health` checks: ffmpeg, whisper engine import, whisper.cpp binary presence, yt‑dlp on PATH, cloud API keys, and basic network.
- Install ffmpeg: macOS `brew install ffmpeg`, Ubuntu `sudo apt-get install -y ffmpeg`.
- Ensure keys are set for cloud engines (Gemini/OpenAI/Deepgram). Engines degrade gracefully if keys are absent.

## Testing
- Runner: `pytest -q` (CI runs on 3.11/3.12/3.13).
- Unit tests emphasize exporters, chunking/stitching, config hash, downloader parsing.
- Cloud engines are monkeypatched to avoid network; chunked offset regressions are covered in `tests/test_chunked_offset.py`.
- Markdown exporter covered in `tests/test_export_md_exporter.py`, utils in `tests/test_export_md_utils.py`, CLI export in `tests/test_cli_export_md.py` and from‑cache in `tests/test_cli_export_md_cache.py`.
- Auto‑chapters covered in `tests/test_export_md_auto_chapters.py`.

## CI & Release
- CI: `.github/workflows/ci.yml` installs ffmpeg, installs the package, runs tests.
- Release: publish as `tubescribe` on PyPI. Tags `vX.Y.Z` have GitHub release notes under `docs/`.

## Coding Guidelines
- Python 3.11+, PEP 8, type hints on public APIs.
- Keep modules focused and functions small; avoid print in library code (use Rich logging).
- Conventional Commits for messages (`feat:`, `fix:`, `docs:`, `test:`, `chore:` etc.).

## Config Quick Reference
- Keys: `GEMINI_API_KEY` / `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `DEEPGRAM_API_KEY` (and optional `ELEVENLABS_API_KEY`).
- Engine defaults/options: `YTX_ENGINE`, `YTX_ENGINE_OPTS` (JSON), `YTX_DEVICE`, `YTX_COMPUTE_TYPE`, `YTX_PREFER_SDK`.
- Timeouts & cache: `YTX_NETWORK_TIMEOUT`, `YTX_DOWNLOAD_TIMEOUT`, `YTX_TRANSCRIBE_TIMEOUT`, `YTX_SUMMARIZE_TIMEOUT`, `YTX_CACHE_DIR`, `YTX_CACHE_TTL_SECONDS|DAYS`.
