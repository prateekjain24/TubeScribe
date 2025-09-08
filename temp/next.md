# Next: Ship TubeScribe (ytx) as a Package

This is a practical checklist to publish the CLI for users who want
`pip install ytx` or `pipx install ytx` with minimal friction.

## 1) Prepare the repo
- Rename repo on GitHub to `TubeScribe` (done).
- Confirm metadata in `ytx/pyproject.toml`:
  - `[project] name = "ytx"` (package name) — keep for now to match CLI command.
  - `Homepage/Repository/Issues` point to `prateekjain24/TubeScribe` (done).
  - Update `version` appropriately (e.g., `0.2.0`).
- Update README badges/links if adding later.
- Ensure license file is present (MIT/Apache/etc.).

## 2) Version bump
- Edit `ytx/pyproject.toml` → `[project].version`.
- Add CHANGELOG entry (optional).
- Commit: `chore(release): vX.Y.Z`.

## 3) Build the artifacts (sdist + wheel)
- Use standard PEP 517 build:
  - `python -m pip install -U build twine`
  - `cd ytx && python -m build`
  - Artifacts appear under `ytx/dist/` (e.g., `ytx-X.Y.Z-py3-none-any.whl`, `ytx-X.Y.Z.tar.gz`).

## 4) Smoke test the wheel
- Create a throwaway venv and install the wheel:
  - `python -m venv .venv-test && source .venv-test/bin/activate`
  - `python -m pip install dist/ytx-*.whl`
  - `ytx --version` and `ytx health` should work.

## 5) Upload to TestPyPI (optional but recommended)
- `python -m twine upload --repository testpypi dist/*`
- Install from TestPyPI to verify metadata and entry points:
  - `python -m pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ytx`
  - Validate `ytx` entry point works.

## 6) Publish to PyPI
- `python -m twine upload dist/*`
- After upload, users can:
  - `pipx install ytx` (recommended)
  - or `pip install ytx`

## 7) Tag + GitHub Release
- `git tag -a vX.Y.Z -m "vX.Y.Z" && git push --tags`
- Create a GitHub release pointing to the tag; include highlights and install instructions.

## 8) Post-release
- Verify `pip install ytx` works in a clean environment.
- Monitor issues and collect feedback.
- Plan next iteration (e.g., ElevenLabs STT, more exporters, CI).

## Notes
- Brand vs package: we keep the CLI/package name as `ytx` to preserve a short command while the repo branding is TubeScribe.
- If you decide to rename the package later (e.g., `tubescribe`), keep `ytx` as a console-script alias for backwards compatibility.

