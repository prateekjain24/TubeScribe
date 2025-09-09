# ytx Configuration Guide

The CLI and engines are configured via environment variables and flags. Most
configuration can be set through `.env` (loaded automatically) or CLI options.

## Environment Variables (YTX_*)

- `GEMINI_API_KEY` (or `GOOGLE_API_KEY`): Gemini API key for cloud engine and summaries.
- `YTX_ENGINE`: default engine (`whisper`, `whispercpp`, or `gemini`).
- `YTX_CACHE_DIR`: override cache root (default XDG: `~/.cache/ytx`).
- `YTX_ENGINE_OPTS`: JSON object of provider‑specific options (e.g., `{"utterances":true}`).
- `YTX_NETWORK_TIMEOUT`: metadata/network timeout (seconds; default 90).
- `YTX_DOWNLOAD_TIMEOUT`: download timeout (seconds; default 1800).
- `YTX_TRANSCRIBE_TIMEOUT`: transcription API timeout (seconds; default 600).
- `YTX_SUMMARIZE_TIMEOUT`: summarization API timeout (seconds; default 180).
- `YTX_CACHE_TTL_SECONDS` / `YTX_CACHE_TTL_DAYS`: optional cache expiration.

### Whisper / faster‑whisper
- `YTX_DEVICE`: `cpu|cuda|auto|metal` (mapped to `cpu` for faster‑whisper).
- `YTX_COMPUTE_TYPE`: `auto|int8|int8_float16|float16|float32`.

### whisper.cpp (Metal)
- `YTX_WHISPERCPP_BIN`: path/name of whisper.cpp binary (e.g., `main`).
- `YTX_WHISPERCPP_NGL`: GPU layers (default 35).
- `YTX_WHISPERCPP_THREADS`: CPU threads (optional).

## CLI Options (selected)

- `--engine`, `--model`: choose engine/model.
- `--timestamps {native,chunked,none}`: timestamp policy.
- `--engine-opts '{"name":value}'`: provider options (JSON).
- `--by-chapter --parallel-chapters --chapter-overlap`: chapter processing.
- `--summarize --summarize-chapters`: summaries (overall/per‑chapter).
- `--output-dir`, `--overwrite`: output location and caching.
- `--max-download-abr-kbps`: select download bit rate (default 96)

## Configuration Hash and Reproducibility

`AppConfig.config_hash()` produces a stable SHA‑256 over key fields that affect
outputs (engine, model, language, device, compute_type, timestamp_policy,
engine_options, and engine‑specific knobs). This hash defines the artifact path
so different configurations don’t collide in the cache.

