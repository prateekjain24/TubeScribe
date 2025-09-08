# TubeScribe v0.3.2 — Export from Cache Fixes

## Fixes
- cache: `scan_cache` and artifact checks now accept legacy `<video_id>.json/.srt` alongside canonical `transcript.json/captions.srt`.
- cli(export): when `transcript.json` is missing, fall back to `<video_id>.json` for cached export.

## Upgrade
`pipx upgrade tubescribe` or `pip install -U tubescribe`

## Notes
This unblocks `ytx export --video-id <id> --to md --output-dir ./notes` on older caches.

