import sys
from pathlib import Path

# Ensure backend/src is on sys.path so tests can import the `backend` package
ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))
