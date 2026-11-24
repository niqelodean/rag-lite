import json
import re
import sys
import os
from statistics import mean

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from retrieve import Retriever

K = 5
QUESTIONS_PATH = "eval/questions.json"


def _build_retriever():
    return Retriever()


def _tokens(text):
    return set(re.findall(r"\w+", text.lower()))


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
    required = {t.lower() for t in must_contain}
    for h in hits[:k]:
        if required <= _tokens(h.get("text", "")):
            return True
    return False


def score_question(q, retriever):
    qid = q["id"]
    expected = q.get("expected_sources") or []
    must = q.get("must_contain") or []
    should_refuse = q.get("should_refuse", False)

    try:
        hits = retriever.search(q["question"], K)
    except Exception as e:
        return {"id": qid, "category": q.get("category", "?"), "error": str(e)}

    top_score = hits[0].get("score", 0.0) if hits else 0.0
    row = {
        "id": qid,
        "category": q.get("category", "uncategorized"),
        "empty": len(hits) == 0,            # ← no more retrieved_files[0] crash
        "top_score": float(top_score),
        "n_hits": len(hits),
    }

    if should_refuse:
        return row  # only empty_rate + top_score are meaningful here

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


def summarise(subset):
    if not subset:
        return {"n": 0}
    scored = [r for r in subset if not r.get("error")]
    return {
        "n": len(subset),
        "errors": sum(1 for r in subset if r.get("error")),
        "hit@1": _mean(r.get("hit@1") for r in scored),
        "hit@3": _mean(r.get("hit@3") for r in scored),
        "hit@5": _mean(r.get("hit@5") for r in scored),
        "mrr": _mean(r.get("mrr") for r in scored),
        "recall@5": _mean(r.get("recall@5") for r in scored),
        "evidence@5": _mean(r.get("evidence@5") for r in scored),
        "empty_rate": round(sum(1 for r in subset if r.get("empty")) / len(subset), 3),
        "top_score_avg": round(mean(r.get("top_score", 0) for r in subset), 3),
    }


def run_evaluation():
    with open(QUESTIONS_PATH) as f:
        test_cases = json.load(f)

    print("Loading retriever...")
    retriever = _build_retriever()
    print(f"Running evaluation on {len(test_cases)} questions (k={K})...\n")

    rows = [score_question(q, retriever) for q in test_cases]
    categories = sorted({r["category"] for r in rows if r.get("category")})

    summary = {"overall": summarise(rows)}
    for cat in categories:
        summary[cat] = summarise([r for r in rows if r["category"] == cat])

    hdr = (f"{'category':<22} {'n':>4} {'err':>4} {'h@1':>6} {'h@3':>6} "
           f"{'h@5':>6} {'mrr':>6} {'r@5':>6} {'ev@5':>6} {'empty':>6} {'top_s':>6}")
    print(hdr)
    print("-" * len(hdr))
    for cat in ["overall"] + categories:
        s = summary[cat]
        if s["n"] == 0:
            continue
        fmt = lambda v: f"{v:.2f}" if isinstance(v, float) else ("-" if v is None else str(v))
        print(f"{cat:<22} {s['n']:>4} {s['errors']:>4} {fmt(s['hit@1']):>6} {fmt(s['hit@3']):>6} "
              f"{fmt(s['hit@5']):>6} {fmt(s['mrr']):>6} {fmt(s['recall@5']):>6} "
              f"{fmt(s['evidence@5']):>6} {fmt(s['empty_rate']):>6} {fmt(s['top_score_avg']):>6}")

    misses = [r for r in rows if r.get("hit@5") is False]
    if misses:
        print(f"\nMisses ({len(misses)}):")
        for r in misses[:20]:
            print(f"  {r['id']:<8} [{r['category']:<20}] top_score={r['top_score']:.2f}")

    errors = [r for r in rows if r.get("error")]
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for r in errors:
            print(f"  {r['id']}: {r['error']}")


if __name__ == "__main__":
    run_evaluation()