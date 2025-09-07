## ytx — YouTube Transcriber (Whisper/Gemini)

CLI to download YouTube audio and transcribe via local Whisper or Gemini. Managed with uv; uses the src layout.

### Quickstart
- Enter project: `cd ytx`
- Sync deps: `uv sync`
- CLI help: `uv run ytx --help`

### Requirements
- Python >= 3.11
- FFmpeg (required for audio extraction/normalization)
  - Check: `ffmpeg -version`
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y ffmpeg`
  - Fedora: `sudo dnf install -y ffmpeg`
  - Arch: `sudo pacman -S ffmpeg`
  - Windows (PowerShell): `winget install Gyan.FFmpeg` or `choco install ffmpeg`

### Restricted videos & cookies
Some videos are age/region restricted or private. Use cookies to authorize yt-dlp when permitted:

- From a local browser session (recommended): pass `cookies_from_browser` as `chrome`, `brave`, or `edge`.
  - Example (Python API): `download_audio(meta, out_dir, cookies_from_browser="chrome")`
  - CLI (future): `--cookies-from-browser chrome`
- From a cookies file: export cookies in Netscape format (e.g., via the "Get cookies.txt LOCALLY" extension) and pass its path.
  - Example (Python API): `download_audio(meta, out_dir, cookies_file="./cookies.txt")`
  - CLI (future): `--cookies ./cookies.txt`

Notes:
- Do not commit cookies to the repo. `.env` is ignored.
- Region restrictions may still apply even with cookies.

### Apple Silicon (Metal) acceleration
- faster-whisper (CTranslate2) does not support Metal directly. For GPU acceleration on M‑series, use whisper.cpp:
  1) Build whisper.cpp with Metal: `make -j METAL=1`
  2) Download a GGUF model (e.g., `gguf-large-v3-turbo.bin`)
  3) Run with engine `whispercpp` or set device=`metal` with engine=`whisper` to auto-prefer whisper.cpp
     - Example: `uv run ytx transcribe <url> --engine whispercpp --model /path/to/gguf-large-v3-turbo.bin`
  4) Optional: set env `YTX_WHISPERCPP_BIN` for the binary path and `YTX_WHISPERCPP_MODEL_PATH` for the model file.
  5) Tuning: `YTX_WHISPERCPP_NGL` (layers on GPU, default 35), `YTX_WHISPERCPP_THREADS` (CPU threads).

### Environment (optional)
- Copy `.env.example` to `.env` and set variables as needed (e.g., `GEMINI_API_KEY`).

### Next Steps
- Implement CLI entry (`ytx/cli.py`) and engines per IMP.md.
