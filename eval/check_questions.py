"""Sanity-check eval/questions.json against the raw docs on disk.

Usage: python eval/check_questions.py --docs-dir docs/
"""
import argparse
import json
import re
import sys
from pathlib import Path


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs-dir", required=True, help="root of your docs (e.g. docs/)")
    args = ap.parse_args()

    docs_root = Path(args.docs_dir)
    if not docs_root.exists():
        sys.exit(f"docs dir not found: {docs_root}")

    questions = json.loads((Path(__file__).parent / "questions.json").read_text())
    bad = 0

    for q in questions:
        qid = q["id"]
        if q.get("should_refuse"):
            continue

        srcs = q.get("expected_sources", [])
        must = q.get("must_contain", [])

        # check every source file exists under docs_root
        missing = [s for s in srcs if not (docs_root / s).exists()]
        if missing:
            print(f"[{qid}] MISSING FILE(S): {missing}")
            bad += 1
            continue

        if not must:
            continue

        text = " ".join((docs_root / s).read_text(errors="ignore") for s in srcs)
        present = _tokens(text)
        missing_terms = [t for t in must if t.lower() not in present]
        if missing_terms:
            print(f"[{qid}] must_contain not found in {srcs}: {missing_terms}")
            bad += 1

    print(f"\n{bad} / {len(questions)} questions need attention.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())