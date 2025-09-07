# Release Checklist

Use this checklist to prepare and ship a new release of ytx.

## Pre‑Release

- [ ] Ensure tests pass locally: `cd ytx && PYTHONPATH=src python -m pytest -q`
- [ ] Verify README and docs reflect current CLI and features
- [ ] Update version in `ytx/pyproject.toml` (`[project] version`)
- [ ] Update `CHANGELOG.md` (if present) with notable changes

## Build & Smoke Test

- [ ] Optional: install in a clean venv with `pip install -e .`
- [ ] Run `ytx --version`, `ytx health` and a quick `transcribe` with a short URL
- [ ] Verify cache artifacts (meta.json, transcript.json, captions.srt, summary.json if applicable)

## Tag & Release

- [ ] Create a Git tag: `git tag -a vX.Y.Z -m "vX.Y.Z" && git push --tags`
- [ ] Draft a GitHub release with release notes
- [ ] Attach any binaries (if distributing helper tools) and link to docs

## Post‑Release

- [ ] Monitor issues and feedback
- [ ] Triage follow‑ups for the next sprint (bugs, docs polish, CI improvements)

