from eval.check_questions import _check_verification_metadata, _doc_freq, _phrase_match


def test_multiword_evidence_phrase_must_exist_in_a_single_chunk():
    chunks = [
        {"source": "guide.md", "text": "query"},
        {"source": "guide.md", "text": "parameters"},
    ]
    assert not any(_phrase_match("query parameters", c["text"]) for c in chunks)


def test_multiword_term_counts_across_chunks_only_when_contiguous_in_one():
    chunks = [
        {"source": "guide.md", "text": "Query parameters are supported."},
        {"source": "index.md", "text": "Query parameters"},
    ]
    assert _doc_freq("query parameters", chunks, exclude_sources={"index.md"}) == 1


def test_verification_fields_are_required_when_verified():
    q = {"verified": True, "verified_by": "Reviewer", "verified_at": "2026-11-25T10:00:00Z"}
    assert _check_verification_metadata(q) == []


def test_verified_at_must_include_a_time():
    q = {"verified": True, "verified_by": "Reviewer", "verified_at": "2026-11-25"}
    assert "'verified_at' must be an ISO-8601 timestamp" in _check_verification_metadata(q)


def test_unverified_question_must_not_claim_a_reviewer():
    q = {"verified": False, "verified_by": "Reviewer", "verified_at": None}
    assert "unverified question must have null 'verified_by' and 'verified_at'" in (
        _check_verification_metadata(q)
    )
