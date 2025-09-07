#!/usr/bin/env bash
set -euo pipefail

# Final integration test helper for a longer YouTube video.
#
# Usage:
#   scripts/integration_e2e.sh <youtube_url> [--engine whisper|gemini] [--model <name>] [--by-chapter]
#
# Examples:
#   scripts/integration_e2e.sh "https://youtu.be/VIDEOID" --engine whisper --model large-v3-turbo --by-chapter
#   scripts/integration_e2e.sh "https://youtu.be/VIDEOID" --engine gemini --timestamps chunked --fallback

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <youtube_url> [--engine ...] [--model ...] [extra ytx flags...]" >&2
  exit 2
fi

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$REPO_ROOT/ytx/src"

URL="$1"; shift || true

echo "[info] Running integration on: $URL" >&2
echo "[info] Health check:" >&2
python3 -m ytx.cli health || true

echo "[info] Starting transcription ..." >&2
set +e
python3 -m ytx.cli transcribe "$URL" "$@"
code=$?
set -e
if [[ $code -ne 0 ]]; then
  echo "[error] Transcription failed with exit code $code" >&2
  exit $code
fi

echo "[info] Locating artifacts in cache ..." >&2
python3 - << 'PY'
import os, json, sys
from pathlib import Path
from ytx.cache import cache_root

root = cache_root()
latest = None
for p in sorted(root.rglob('*.json')):
    if p.name == 'meta.json' or p.name == 'summary.json':
        continue
    if p.stat().st_size > 512:
        latest = p
print('Cache root:', root)
if latest is None:
    print('No transcript JSON found under cache root', file=sys.stderr)
    sys.exit(1)
payload = json.loads(latest.read_text(encoding='utf-8'))
vid = payload.get('video_id'); segs = payload.get('segments', [])
print('Transcript:', latest)
print('Video ID:', vid, '| Segments:', len(segs))
PY

echo "[info] Integration finished." >&2

