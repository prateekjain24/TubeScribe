# TubeScribe v0.2.2

## Highlights
- CLI health: adds checks for `whisper_engine` (faster-whisper), `whispercpp_bin`, `yt-dlp`, and cloud provider keys (`OPENAI_API_KEY`, `DEEPGRAM_API_KEY`).
- README: clickable badges, downloads badge, and Health Reference section.

## Install
- `pipx install tubescribe` (or `pip install tubescribe`)
- Verify: `ytx --version` or `tubescribe --version`

## Health
- Run: `ytx health`
- Green tips: install FFmpeg; set optional keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`); ensure `yt-dlp` and whisper.cpp are available if you use those engines.

## Links
- PyPI: https://pypi.org/project/tubescribe/0.2.2/
- Repo: https://github.com/prateekjain24/TubeScribe
- Notes: see `docs/RELEASE_NOTES.md` (v0.2.2)

