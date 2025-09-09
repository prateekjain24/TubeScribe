# TubeScribe v0.3.6 — Python 3.10–3.13 + Faster Downloads

## Highlights
- Downloader: avoid extra re‑encode during download by default. We download the source audio and normalize once to 16 kHz WAV. New flag `--download-extract-audio` restores yt‑dlp FFmpegExtractAudio when you need a predictable container.
- Python support: now supports Python 3.10–3.13 (classifiers + CI). Docs updated to Python 3.10+.

## Also recent
- `--max-download-abr-kbps <N>` (default 96) to cap YouTube audio bitrate; reduces size/time without practical ASR loss.
- Markdown export with optional auto‑chapters (when the video has none): `--md-auto-chapters-min N`.

## Upgrade
`pipx upgrade tubescribe` or `pip install -U tubescribe`

