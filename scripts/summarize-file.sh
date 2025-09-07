#!/usr/bin/env bash
set -euo pipefail

# Summarize an existing TranscriptDoc JSON using the source tree without installing.
# Usage: scripts/summarize-file.sh ytx/0jpcFxY_38k.json [--language en]

repo_root=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$repo_root/ytx/src"

cd "$repo_root/ytx"
exec python3 -m ytx.cli summarize-file "$@"

