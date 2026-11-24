"""Sanity-check eval/questions.json against the indexed chunks.

Validates against data/chunks.json (what the retriever actually sees), not the
raw docs dir — so a term that passes also guarantees it appears in a real chunk.

Checks:
  - Answerable questions: expected_sources are in the index, must_contain terms
    appear in those chunks (phrase-aware for multi-word terms), and evidence
    terms aren't too generic to be useful.
  - Refuse questions: every topic_term is absent from documentation chunks
    (changelog/navigation files are excluded — a passing mention there does not
    count as "documented").

Usage:
    python eval/check_questions.py
    python eval/check_questions.py --chunks data/chunks.json --questions eval/questions.json

NOTE: The old --docs-dir flag is gone. If you've updated data/docs/, run ingest
first so chunks.json reflects the new snapshot.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Files that are navigation or changelog, not documentation. A topic mentioned
# only here is still "out of scope" for refuse questions.
NON_DOC_FILES = {
    "release-notes.md",
    "index.md",
    "benchmarks.md",
    "fastapi-people.md",
}

# Evidence term appearing in more than this fraction of chunks is too generic
# to prove retrieval found the right chunk.
GENERIC_THRESHOLD = 0.05

# Topic term can appear in at most this many doc chunks and still count as
# "undocumented" (allows one stray mention).
REFUSE_MAX_DOC_CHUNKS = 1


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _phrase_match(term: str, text: str) -> bool:
    """Multi-word terms must appear as a contiguous phrase; single words match tokens."""
    term_lower = term.lower()
    if " " in term_lower:
        return term_lower in text.lower()
    return term_lower in _tokens(text)


def _doc_freq(term: str, chunks, exclude_sources=None) -> int:
    exclude = exclude_sources or set()
    return sum(
        1 for c in chunks
        if c.get("source") not in exclude and _phrase_match(term, c.get("text", ""))
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default="data/chunks.json")
    ap.add_argument("--questions", default="eval/questions.json")
    args = ap.parse_args()

    chunks_path = Path(args.chunks)
    questions_path = Path(args.questions)
    if not chunks_path.exists():
        sys.exit(f"chunks not found: {chunks_path}\nRun your ingest script first.")
    if not questions_path.exists():
        sys.exit(f"questions not found: {questions_path}")

    chunks = json.loads(chunks_path.read_text())
    questions = json.loads(questions_path.read_text())

    if not chunks:
        sys.exit(f"chunks file is empty: {chunks_path}")

    by_source: dict[str, list[str]] = {}
    for c in chunks:
        by_source.setdefault(c["source"], []).append(c.get("text", ""))

    total_chunks = len(chunks)
    errors = 0
    warnings = 0

    print(f"Checking {len(questions)} questions against {total_chunks} chunks "
          f"({len(by_source)} sources) from {chunks_path}\n")

    for q in questions:
        qid = q["id"]

        # ── Refuse questions: topic_terms must be absent from real docs ──
        if q.get("should_refuse"):
            terms = q.get("topic_terms") or []
            if not terms:
                print(f"[{qid}] ERROR: refuse question has no topic_terms — cannot verify scope")
                errors += 1
                continue
            for t in terms:
                df = _doc_freq(t, chunks, exclude_sources=NON_DOC_FILES)
                if df > REFUSE_MAX_DOC_CHUNKS:
                    print(f"[{qid}] ERROR: topic_term '{t}' appears in {df} doc chunks "
                          f"(max {REFUSE_MAX_DOC_CHUNKS}) — topic is not truly out of scope")
                    errors += 1
            continue

        # ── Answerable questions: sources indexed, must_contain present, not generic ──
        srcs = q.get("expected_sources") or []
        if not srcs:
            print(f"[{qid}] ERROR: answerable question has no expected_sources")
            errors += 1
            continue

        missing = [s for s in srcs if s not in by_source]
        if missing:
            print(f"[{qid}] ERROR: expected source(s) not in index: {missing}")
            errors += 1
            continue

        must = q.get("must_contain") or []
        if not must:
            continue

        source_text = " ".join(t for s in srcs for t in by_source[s])
        for term in must:
            if not _phrase_match(term, source_text):
                print(f"[{qid}] ERROR: must_contain '{term}' not found in any chunk of {srcs}")
                errors += 1
                continue
            df = _doc_freq(term, chunks)
            pct = df / total_chunks
            if pct > GENERIC_THRESHOLD:
                print(f"[{qid}] WARN: must_contain '{term}' appears in {df}/{total_chunks} "
                      f"chunks ({pct:.1%}) — weak evidence term, evidence@5 is near-automatic")
                warnings += 1

    print(f"\n{errors} error(s), {warnings} warning(s), {len(questions)} questions total.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())