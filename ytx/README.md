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

### Environment (optional)
- Copy `.env.example` to `.env` and set variables as needed (e.g., `GEMINI_API_KEY`).

### Next Steps
- Implement CLI entry (`ytx/cli.py`) and engines per IMP.md.
