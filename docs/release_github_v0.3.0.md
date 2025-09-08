# TubeScribe v0.3.0 — Notes‑Ready Markdown Export

## Highlights
- MarkdownExporter (`md`) turns transcripts into polished notes:
  - Optional YAML frontmatter (Obsidian‑friendly)
  - Title linked to YouTube
  - TL;DR + key bullets (if present)
  - Chapter outline with clickable timestamps
  - Optional transcript section
- New CLI command: `ytx export`
  - From cache: `ytx export --video-id <id> --to md --output-dir ./notes --md-frontmatter`
  - From file: `ytx export --from-file /path/to/<id>.json --to md --output-dir ./notes`

## Example
```
---
title: Sample Title
url: https://youtu.be/ABCDEFGHIJK
date: 2025-09-08
duration: 12:34
engine: gemini
model: gemini-2.5-flash
tags: [youtube, transcript]
---

# [Sample Title](https://youtu.be/ABCDEFGHIJK)

## Summary
One‑paragraph TL;DR here

## Key Points
- Point A
- Point B

## Chapters
### [0:00](https://youtu.be/ABCDEFGHIJK?t=0) Intro
### [5:23](https://youtu.be/ABCDEFGHIJK?t=323) Main Topic
```

## Install / Upgrade
`pipx install tubescribe` or `pip install -U tubescribe`

## Links
- PyPI: https://pypi.org/project/tubescribe/
- Repo: https://github.com/prateekjain24/TubeScribe
- Changelog: see `docs/RELEASE_NOTES.md` (v0.3.0)

