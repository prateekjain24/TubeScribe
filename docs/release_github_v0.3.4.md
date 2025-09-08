# TubeScribe v0.3.4 — Auto‑Chapters for Markdown

## Feature
- Markdown export can now synthesize chapters when a video has none.
  - CLI: `--md-auto-chapters-min N` adds a chapter outline every N minutes.
  - Works alongside existing features: frontmatter, summary/bullets, transcript.

## Example
`ytx export --video-id <id> --to md --output-dir ./notes --md-frontmatter --md-auto-chapters-min 5`

## Upgrade
`pipx upgrade tubescribe` or `pip install -U tubescribe`

