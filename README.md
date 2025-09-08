TubeScribe (ytx) — Fast YouTube Transcription & Captions
========================================================

Repository: https://github.com/prateekjain24/TubeScribe

TubeScribe (CLI command: `ytx`) downloads YouTube audio, normalizes it, transcribes with your chosen engine, and writes clean transcript JSON + SRT captions. It includes smart caching, chapter processing, and optional summarization.

Quickstart (≈ 2 minutes)
1) Prereqs
- Python 3.11+
- FFmpeg on PATH (check: `ffmpeg -version`)

2) Install (dev)
- Recommended: venv + pip
  - `cd ytx && python3.11 -m venv .venv && source .venv/bin/activate`
  - `python -m pip install -U pip setuptools wheel`
  - `python -m pip install -e .`
- Or without installing: from repo root → `export PYTHONPATH="$(pwd)/ytx/src" && cd ytx && python3 -m ytx.cli --help`

3) Health check
- `ytx health`  (checks ffmpeg, API key presence, and basic network)

4) Transcribe (local Whisper)
- `ytx transcribe "https://youtu.be/<VIDEOID>" --engine whisper --model small`

Engines at a glance
- Whisper (local, faster‑whisper): fast on CPU/GPU; default.
- Whisper.cpp (Metal): on Apple Silicon; pass `--engine whispercpp --model /path/to/model.gguf`.
- Gemini (cloud): best‑effort timestamps; recommended `--timestamps chunked --fallback`.
- OpenAI (cloud): `--engine openai` (SDK‑first optional; HTTP fallback).
- Deepgram (cloud): `--engine deepgram` (SDK‑first optional; HTTP fallback).
- ElevenLabs (cloud): stub in place; STT support pending.

Common flags
- `--engine whisper|whispercpp|gemini|openai|deepgram` — choose an engine
- `--model <name>` — engine model (e.g., small, large-v3-turbo, gemini-2.5-flash, whisper-1)
- `--timestamps native|chunked|none` — timestamp policy (chunked recommended for LLM engines)
- `--engine-opts '{"k":v}'` — provider options (e.g., Deepgram: `{"utterances":true,"smart_format":true}`)
- `--by-chapter --parallel-chapters --chapter-overlap 2.0` — process chapters in parallel
- `--summarize --summarize-chapters` — overall TL;DR + bullets; per‑chapter summaries
- `--output-dir ./artifacts` — write outputs outside the cache dir
- `--overwrite` — ignore cache and reprocess
- `--fallback` — on Gemini errors, fallback to Whisper
- `--debug` — verbose logs

Examples
- Whisper (CPU):
  - `ytx transcribe "https://youtu.be/<VIDEOID>" --engine whisper --model small`
- Whisper (Metal via whisper.cpp):
  - `ytx transcribe "https://youtu.be/<VIDEOID>" --engine whispercpp --model /path/to/gguf-large-v3-turbo.bin`
- Gemini (chunked timestamps + fallback):
  - `ytx transcribe "https://youtu.be/<VIDEOID>" --engine gemini --timestamps chunked --fallback`
- OpenAI (verbose segments when available):
  - `ytx transcribe "https://youtu.be/<VIDEOID>" --engine openai --timestamps native`
- Deepgram (utterances):
  - `ytx transcribe "https://youtu.be/<VIDEOID>" --engine deepgram --engine-opts '{"utterances":true,"smart_format":true}' --timestamps native`
- Chapters + summaries:
  - `ytx transcribe "https://youtu.be/<VIDEOID>" --by-chapter --parallel-chapters --chapter-overlap 2.0 --summarize-chapters --summarize`
- Summarize an existing transcript JSON:
  - `ytx summarize-file /path/to/<video_id>.json --write`

Configuration (copy `.env.example` → `.env`)
- Cloud keys: `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)
- Engine defaults: `YTX_ENGINE`, `WHISPER_MODEL`
- Engine options: `YTX_ENGINE_OPTS` (JSON), `YTX_PREFER_SDK=true` (prefer SDK for OpenAI/Deepgram)
- Timeouts: `YTX_NETWORK_TIMEOUT`, `YTX_DOWNLOAD_TIMEOUT`, `YTX_TRANSCRIBE_TIMEOUT`, `YTX_SUMMARIZE_TIMEOUT`
- Cache: `YTX_CACHE_DIR`, `YTX_CACHE_TTL_SECONDS|DAYS`
- whisper.cpp: `YTX_WHISPERCPP_BIN`, `YTX_WHISPERCPP_NGL`, `YTX_WHISPERCPP_THREADS`

Outputs & cache
- JSON: `<video_id>.json` (TranscriptDoc) — includes segments; optionally `chapters` and `summary`.
- SRT: `<video_id>.srt` — wrapped captions.
- Cache layout (XDG): `~/.cache/ytx/<video_id>/<engine>/<model>/<config_hash>/`
  - `transcript.json`, `captions.srt`, `meta.json` (provenance), `summary.json` (if generated)

Apple Silicon (whisper.cpp)
- Build: `make -j METAL=1` in whisper.cpp
- Run: `ytx transcribe ... --engine whispercpp --model /path/to/model.gguf`
- Tuning: `YTX_WHISPERCPP_NGL` (30–40 typical), `YTX_WHISPERCPP_THREADS`

Troubleshooting
- “ffmpeg not found”: install FFmpeg and ensure it’s on PATH (see Requirements).
- “Restricted / Private / Age‑restricted”: use cookies with yt‑dlp outside the tool to download audio locally, then run `ytx summarize-file` on the transcript.
- “No module named ytx”: avoid running `ytx` from inside the `ytx/` folder; or use module form: `PYTHONPATH=ytx/src python -m ytx.cli …`
- Gemini timestamps: best‑effort; prefer `--timestamps chunked` for reliable coarse timings.

Useful commands
- Health: `ytx health`
- Update check: `ytx update-check`
- Cache: `ytx cache ls | ytx cache stats | ytx cache clear --yes`

Contributing
- Code lives under `ytx/src/ytx/` (CLI: `cli.py`). Tests under `ytx/tests/`.
- Run tests: `cd ytx && PYTHONPATH=src python -m pytest -q`
- Lint (if configured): `ruff check .`
