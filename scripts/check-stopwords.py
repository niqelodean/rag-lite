import sys
from pathlib import Path

# Make the repo root importable when running as `python scripts/check-stopwords.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from retrieve import STOPWORDS

for w in ["work", "need", "want", "how", "the"]:
    print(w, "->", w in STOPWORDS)