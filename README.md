ytx — YouTube Transcriber (Whisper / Metal via whisper.cpp)
==========================================================

CLI that downloads YouTube audio and produces transcripts and captions using:
- Local Whisper (faster-whisper / CTranslate2)
- Whisper.cpp (Metal acceleration on Apple Silicon)

Managed with uv, using the `src` layout.

Features
- One command: URL → audio → normalized WAV → transcript JSON + SRT captions
- Engines: `whisper` (faster-whisper) and `whispercpp` (Metal via whisper.cpp)
- Rich progress for download + transcription
- Deterministic JSON (orjson) and SRT line wrapping

Requirements
- Python >= 3.11
- FFmpeg installed and on PATH
  - Check: `ffmpeg -version`
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y ffmpeg`
  - Fedora: `sudo dnf install -y ffmpeg`
  - Arch: `sudo pacman -S ffmpeg`
  - Windows: `winget install Gyan.FFmpeg` or `choco install ffmpeg`

Install (dev)
- Option A: venv + pip (recommended)
  - `cd ytx && python3.11 -m venv .venv && source .venv/bin/activate`
  - `python -m pip install -U pip setuptools wheel`
  - `python -m pip install -e .`
  - Run: `ytx --help`
- Option B: uv
  - `cd ytx && uv sync`
  - Run: `uv run ytx --help`

Running locally without installing
- Module form avoids PATH and shadowing issues:
  - From repo root:
    - `export PYTHONPATH="$(pwd)/ytx/src"`
    - `cd ytx && python3 -m ytx.cli --help`
  - Example (summarize existing transcript):
    - `python3 -m ytx.cli summarize-file 0jpcFxY_38k.json --write`

Note on namespace shadowing
- Avoid running the `ytx` console script from inside the `ytx/` folder when using editable installs.
- Inside that folder, Python may resolve `import ytx` to the folder instead of the installed package.
- Prefer the module form (`python -m ytx.cli …`) or run console scripts from the repo root.

Usage (CLI)
- Whisper (CPU by default):
  - `ytx transcribe <url> --engine whisper --model small`
- Whisper (larger model):
  - `ytx transcribe <url> --engine whisper --model large-v3-turbo`
- Choose output directory:
  - `ytx transcribe <url> --engine whisper --output-dir ./artifacts`
- Verbose logging:
  - `ytx --verbose transcribe <url> --engine whisper`
- Summarize an existing transcript JSON:
  - `ytx summarize-file /path/to/<video_id>.json --write`

Metal (Apple Silicon) via whisper.cpp
- Build whisper.cpp with Metal: `make -j METAL=1`
- Download a GGUF/GGML model (e.g., large-v3-turbo)
- Run with whisper.cpp engine by passing a model file path:
  - `uv run ytx transcribe <url> --engine whispercpp --model /path/to/gguf-large-v3-turbo.bin`
- Auto-prefer whisper.cpp when `device=metal` (if `whisper.cpp` binary is available):
  - Set env `YTX_WHISPERCPP_BIN` to the `main` binary path, and provide a model path as above
- Tuning (env or .env):
  - `YTX_WHISPERCPP_NGL` (GPU layers, default 35), `YTX_WHISPERCPP_THREADS` (CPU threads)

Outputs
- JSON (`<video_id>.json`): TranscriptDoc
  - keys: `video_id, source_url, title, duration, language, engine, model, created_at, segments[]`
  - segment: `{id, start, end, text, confidence?}` (seconds for time)
- SRT (`<video_id>.srt`): line-wrapped captions (2 lines max)

Configuration (.env)
- Copy `.env.example` → `.env`, then adjust:
  - `YTX_ENGINE` (default `whisper`) and `WHISPER_MODEL` (e.g., `large-v3-turbo`)
  - `GEMINI_API_KEY` (for Gemini transcription/summarization)
  - `YTX_WHISPERCPP_BIN` and `YTX_WHISPERCPP_MODEL_PATH` for whisper.cpp
  - Optional: `YTX_CACHE_DIR`, `YTX_OUTPUT_DIR`, concurrency and timeouts

Restricted videos & cookies
- Some videos are age/region restricted or private. The downloader supports cookies, but CLI flags are not yet wired.
- Workarounds: run yt-dlp manually, or use the Python API (pass `cookies_from_browser` / `cookies_file` to downloader).
- Error messages suggest cookies usage when restrictions are detected.

Performance Tips
- faster‑whisper: `compute_type=auto` resolves to `int8` on CPU, `float16` on CUDA.
- Model sizing: start with `small`/`medium`; use `large-v3(-turbo)` for best quality.
- Metal (whisper.cpp): tune `-ngl` (30–40 typical on M‑series) and threads to maximize throughput.

Development
- Structure: code in `src/ytx/`, CLI in `src/ytx/cli.py`, engines in `src/ytx/engines/`, exporters in `src/ytx/exporters/`.
- Tests: `uv run pytest -q` (add tests under `ytx/tests/`).
- Lint/format (if configured): `uv run ruff check .` / `uv run ruff format .`.

Roadmap
- Add VTT/TXT exporters, format selection (`--formats json,srt,vtt,txt`)
- Chapters-aware transcription and summaries
- Gemini transcription/summarization option
- Caching and resume for repeat runs
