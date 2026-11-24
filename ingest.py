import requests
from pathlib import Path
import argparse

FASTAPI_REPO = "https://api.github.com/repos/fastapi/fastapi"
RAW_REPO = "https://raw.githubusercontent.com/fastapi/fastapi"
# Pin the corpus by default so repeated ingests use the same documentation.
DEFAULT_DOCS_REF = "05e6df7e906c3decba377c37548019973f40bf15"

parser = argparse.ArgumentParser(description="Download FastAPI English Markdown docs.")
parser.add_argument("--ref", default=DEFAULT_DOCS_REF,
                    help="FastAPI git ref or commit SHA (default: pinned commit)")
args = parser.parse_args()
docs_ref = args.ref

# --- 1. Get the file list from the pinned FastAPI ref (one API call) ---
tree_url = f"{FASTAPI_REPO}/git/trees/{docs_ref}?recursive=1"
tree_response = requests.get(tree_url)
if tree_response.status_code != 200:
    print("Tree call returned status", tree_response.status_code)
    print(tree_response.text[:500])
    raise SystemExit

all_files = tree_response.json()["tree"]

# --- 3. Download only the English markdown docs ---
out_dir = Path("data/docs")
out_dir.mkdir(parents=True, exist_ok=True)

count = 0
for item in all_files:
    path = item["path"]

    if not path.startswith("docs/en/docs/"):
        continue
    if not path.endswith(".md"):
        continue

    raw_url = f"{RAW_REPO}/{docs_ref}/{path}"
    text = requests.get(raw_url).text

    local_path = out_dir / path.replace("docs/en/docs/", "")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(text, encoding="utf-8")

    count = count + 1
    if count % 20 == 0:
        print("downloaded", count, "files so far...")

print(f"done. total files: {count}; FastAPI ref: {docs_ref}")
