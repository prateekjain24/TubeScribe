# TubeScribe v0.3.5 — Download Bitrate Cap

## Feature
- New flag: `--max-download-abr-kbps <N>` (default 96). Caps YouTube audio bitrate during download via yt‑dlp format selector `bestaudio[abr<=N]/bestaudio`.
  - Reduces download size/time without practical ASR accuracy loss.
  - Set to 0 to disable (use bestaudio/best).

## Upgrade
`pipx upgrade tubescribe` or `pip install -U tubescribe`

## Example
`ytx transcribe "https://www.youtube.com/watch?v=..." --engine gemini --timestamps chunked --fallback --max-download-abr-kbps 96`

