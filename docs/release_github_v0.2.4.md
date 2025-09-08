# TubeScribe v0.2.4

## Highlights
- Chunked engines: fixed segment offset logic to avoid in-place mutation of validated models.
  - Gemini: safe offset when stitching chunks.
  - OpenAI & Deepgram: applied the same fix to prevent `end <= start` validation errors.
- Tests: added regression tests to ensure chunked offsets never violate `end > start`.

## Install / Upgrade
- `pipx install tubescribe` or `pip install -U tubescribe`
- Verify: `ytx --version` or `tubescribe --version`

## Links
- PyPI: https://pypi.org/project/tubescribe/0.2.4/
- Repo: https://github.com/prateekjain24/TubeScribe
- Changelog: see `docs/RELEASE_NOTES.md` (v0.2.4)

