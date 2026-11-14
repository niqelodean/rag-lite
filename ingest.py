import requests
from pathlib import Path

# --- 1. Ask GitHub what the default branch is ---
repo_info = requests.get("https://api.github.com/repos/fastapi/fastapi")
if repo_info.status_code != 200:
    print("GitHub API returned status", repo_info.status_code)
    print(repo_info.text[:500])
    raise SystemExit

branch = repo_info.json()["default_branch"]

# --- 2. Get a list of every file in the repo (one API call) ---
tree_url = f"https://api.github.com/repos/fastapi/fastapi/git/trees/{branch}?recursive=1"
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

    raw_url = f"https://raw.githubusercontent.com/fastapi/fastapi/{branch}/{path}"
    text = requests.get(raw_url).text

    local_path = out_dir / path.replace("docs/en/docs/", "")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(text, encoding="utf-8")

    count = count + 1
    if count % 20 == 0:
        print("downloaded", count, "files so far...")

print("done. total files:", count)