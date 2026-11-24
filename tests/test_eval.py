from eval.runeval import score_question, summarise_answerable, summarise_refuse


class FakeRetriever:
    def __init__(self, hits, raw):
        self.hits = hits
        self.raw = raw

    def search(self, _query, _k):
        return self.hits

    def raw_scores(self, _query):
        return self.raw


def test_answerable_metrics_use_filtered_hits_and_keep_raw_score():
    question = {
        "id": "q1",
        "category": "single_fact",
        "question": "Where is it documented?",
        "expected_sources": ["guide.md"],
        "must_contain": ["query parameters"],
    }
    hits = [{"source": "guide.md", "text": "Query parameters are values.", "score": 3.5}]

    row = score_question(question, FakeRetriever(hits, [(0, 4.25)]))

    assert row["raw_top_score"] == 4.25
    assert row["post_min_score_top"] == 3.5
    assert row["hit@1"] is True
    assert row["evidence@5"] is True


def test_empty_filtered_results_still_report_raw_top_score():
    question = {
        "id": "q2", "category": "single_fact", "question": "query params",
        "expected_sources": ["guide.md"], "must_contain": ["query parameters"],
    }

    row = score_question(question, FakeRetriever([], [(0, 0.75)]))

    assert row["empty"] is True
    assert row["raw_top_score"] == 0.75
    assert row["post_min_score_top"] == 0.0


def test_refusal_question_does_not_get_answerable_retrieval_metrics():
    question = {
        "id": "q3", "category": "should_refuse", "question": "unsupported",
        "should_refuse": True,
    }

    row = score_question(question, FakeRetriever([], [(0, 8.0)]))

    assert row["raw_top_score"] == 8.0
    assert "hit@5" not in row
    assert "evidence@5" not in row


def test_refuse_summary_uses_true_median_for_even_sample():
    rows = [
        {"should_refuse": True, "raw_top_score": score,
         "post_min_score_top": score, "empty": False}
        for score in (1.0, 3.0, 9.0, 11.0)
    ]

    summary = summarise_refuse(rows)

    assert summary["raw_min"] == 1.0
    assert summary["raw_median"] == 6.0
    assert summary["raw_max"] == 11.0


def test_answerable_summary_excludes_refusal_rows():
    rows = [
        {"should_refuse": False, "hit@1": True, "hit@3": True, "hit@5": True,
         "mrr": 1.0, "recall@5": 1.0, "evidence@5": True},
        {"should_refuse": True, "raw_top_score": 100.0},
    ]

    summary = summarise_answerable(rows)

    assert summary["n"] == 1
    assert summary["hit@1"] == 1.0
