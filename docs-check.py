from pathlib import Path
from collections import Counter

folder_counts = Counter()
total_files = 0

for path in Path("data/docs").rglob("*.md"):
    total_files += 1
    parent = path.parent.name if path.parent.name != "docs" else "(top level)"
    folder_counts[parent] += 1

print("total .md files:", total_files)
print()
for name, count in sorted(folder_counts.items()):
    print(name + ":", count, "files")