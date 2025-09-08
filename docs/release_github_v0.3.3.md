# TubeScribe v0.3.3 — Cache Parsing Fix

## Fixes
- cache: correct parent directory parsing for `<root>/<video>/<engine>/<model>/<hash>`, so `video_id` is detected correctly during cache scans.
- tests: add coverage for cache scan + `video_id` parsing.

## Why
Stabilizes `ytx export --video-id <id> --to md ...` and `ytx cache ls` on existing caches.

## Upgrade
`pipx upgrade tubescribe` or `pip install -U tubescribe`

