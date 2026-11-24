"""Retrieval eval harness for rag-lite.

Usage:
    python eval/runeval.py
"""
import json
import re
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from retrieve import Retriever

K = 5
QUESTIONS_PATH = Path(__file__).parent / "questions.json"


def _build_retriever():
    return Retriever()


def _tokens(text):
    return set(re.findall(r"\w+", text.lower()))


def _phrase_match(term, text):
    term_lower = term.lower()
    if " " in term_lower:
        return term_lower in text.lower()
    return term_lower in _tokens(text)


def _hit_at(hits, expected, k):
    if not expected:
        return None
    return any(h["source"] in expected for h in hits[:k])


def _recall_at(hits, expected, k):
    if not expected:
        return None
    seen = {h["source"] for h in hits[:k]}
    return len(seen & set(expected)) / len(expected)


def _mrr(hits, expected):
    if not expected:
        return None
    for rank, h in enumerate(hits, 1):
        if h["source"] in expected:
            return 1.0 / rank
    return 0.0


def _evidence_at(hits, must_contain, k):
    if not must_contain:
        return None
    for h in hits[:k]:
        text = h.get("text", "")
        if all(_phrase_match(t, text) for t in must_contain):
            return True
    return False


def score_question(q, retriever):
    qid = q["id"]
    expected = q.get("expected_sources") or []
    must = q.get("must_contain") or []
    should_refuse = q.get("should_refuse", False)

    try:
        hits = retriever.search(q["question"], K)
        raw = retriever.raw_scores(q["question"])
    except Exception as e:
        return {"id": qid, "category": q.get("category", "?"), "error": str(e)}

    row = {
        "id": qid,
        "category": q.get("category", "uncategorized"),
        "should_refuse": should_refuse,
        "empty": len(hits) == 0,
        "n_hits": len(hits),
        "raw_top_score": float(raw[0][1]) if raw else 0.0,
        "post_min_score_top": float(hits[0]["score"]) if hits else 0.0,
    }

    if should_refuse:
        return row

    row["hit@1"] = _hit_at(hits, expected, 1)
    row["hit@3"] = _hit_at(hits, expected, 3)
    row["hit@5"] = _hit_at(hits, expected, 5)
    row["mrr"] = _mrr(hits, expected)
    row["recall@5"] = _recall_at(hits, expected, K)
    row["evidence@5"] = _evidence_at(hits, must, K)
    return row


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return round(mean(vals), 3) if vals else None


def summarise_answerable(subset):
    ans = [r for r in subset if not r.get("should_refuse") and not r.get("error")]
    if not ans:
        return {"n": 0}
    return {
        "n": len(ans),
        "hit@1": _mean(r.get("hit@1") for r in ans),
        "hit@3": _mean(r.get("hit@3") for r in ans),
        "hit@5": _mean(r.get("hit@5") for r in ans),
        "mrr": _mean(r.get("mrr") for r in ans),
        "recall@5": _mean(r.get("recall@5") for r in ans),
        "evidence@5": _mean(r.get("evidence@5") for r in ans),
    }


def summarise_refuse(subset):
    ref = [r for r in subset if r.get("should_refuse") and not r.get("error")]
    if not ref:
        return {"n": 0}
    raw = sorted(r["raw_top_score"] for r in ref)
    post = sorted(r["post_min_score_top"] for r in ref)
    n = len(raw)
    return {
        "n": n,
        "raw_min": round(raw[0], 2),
        "raw_median": round(raw[n // 2], 2),
        "raw_max": round(raw[-1], 2),
        "post_min": round(min(post), 2),
        "empty_rate": round(sum(1 for r in ref if r.get("empty")) / n, 3),
    }


def main():
    with open(QUESTIONS_PATH) as f:
        questions = json.load(f)

    print("Loading retriever...")
    retriever = _build_retriever()
    print(f"Running evaluation on {len(questions)} questions (k={K})...\n")

    rows = [score_question(q, retriever) for q in questions]

    categories = sorted({r["category"] for r in rows if r.get("category")})
    answerable_rows = [r for r in rows if not r.get("should_refuse")]
    refuse_rows = [r for r in rows if r.get("should_refuse")]

    overall = summarise_answerable(answerable_rows)
    refuse = summarise_refuse(refuse_rows)

    # ── Answerable table ────────────────────────────────────────────────
    print("ANSWERABLE QUESTIONS")
    hdr = f"{'category':<22} {'n':>4} {'h@1':>6} {'h@3':>6} {'h@5':>6} {'mrr':>6} {'r@5':>6} {'ev@5':>6}"
    print(hdr)
    print("-" * len(hdr))

    def _fmt(v):
        return f"{v:.2f}" if isinstance(v, float) else ("-" if v is None else str(v))

    print(f"{'overall':<22} {overall['n']:>4} {_fmt(overall['hit@1']):>6} {_fmt(overall['hit@3']):>6} "
          f"{_fmt(overall['hit@5']):>6} {_fmt(overall['mrr']):>6} {_fmt(overall['recall@5']):>6} "
          f"{_fmt(overall['evidence@5']):>6}")
    for cat in categories:
        if cat == "should_refuse":
            continue
        s = summarise_answerable([r for r in rows if r["category"] == cat])
        if s["n"] == 0:
            continue
        print(f"{cat:<22} {s['n']:>4} {_fmt(s['hit@1']):>6} {_fmt(s['hit@3']):>6} "
              f"{_fmt(s['hit@5']):>6} {_fmt(s['mrr']):>6} {_fmt(s['recall@5']):>6} "
              f"{_fmt(s['evidence@5']):>6}")

    # ── Refuse block ────────────────────────────────────────────────────
    if refuse["n"]:
        print("\nSHOULD_REFUSE (raw scores, pre-MIN_SCORE)")
        print(f"  n={refuse['n']}  raw_min={refuse['raw_min']}  raw_median={refuse['raw_median']}  "
              f"raw_max={refuse['raw_max']}  post_min_filter_top={refuse['post_min']}  "
              f"empty_rate={refuse['empty_rate']}")

        # The actual tuning signal
        ans_raw_min = min(
            (r["raw_top_score"] for r in answerable_rows if r.get("raw_top_score") is not None),
            default=0.0,
        )
        print(f"\n  Separation: answerable raw_min={ans_raw_min:.2f} vs "
              f"refuse raw_max={refuse['raw_max']:.2f}")
        if refuse["raw_max"] >= ans_raw_min:
            print(f"  → distributions OVERLAP — no MIN_SCORE can cleanly separate "
                  f"answerable from refuse. Refusal must happen at LLM layer.")
        else:
            print(f"  → clean gap exists — MIN_SCORE in ({refuse['raw_max']:.2f}, "
                  f"{ans_raw_min:.2f}) separates them.")

    # ── Misses ──────────────────────────────────────────────────────────
    misses = [r for r in answerable_rows if r.get("hit@5") is False]
    if misses:
        print(f"\nMisses ({len(misses)}):")
        for r in misses:
            print(f"  {r['id']:<8} [{r['category']:<20}] raw_top={r['raw_top_score']:.2f}")

    errors = [r for r in rows if r.get("error")]
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for r in errors:
            print(f"  {r['id']}: {r['error']}")


if __name__ == "__main__":
    main()