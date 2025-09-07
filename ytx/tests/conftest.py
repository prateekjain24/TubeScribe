import sys
from pathlib import Path


# Ensure src/ on sys.path for imports when running tests from project dir
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

