import json

import pytest

import retrieve
from retrieve import Retriever, tokenize


# --- tokenize --------------------------------------------------------------

def test_tokenize_lowercases_and_splits_on_punctuation():
    assert tokenize("Path-Parameters, Query!") == ["path", "parameters", "query"]


def test_tokenize_drops_stopwords():
    assert tokenize("How do I use the Depends") == ["use", "depends"]


def test_tokenize_treats_work_as_a_stopword():
    # "work"/"need"/"want" are deliberately filtered: they match too many chunks.
    assert tokenize("how do path parameters work") == ["path", "parameters"]


@pytest.mark.parametrize("text", ["", "   ", "how do I", "?!..."])
def test_tokenize_returns_empty_list_when_nothing_meaningful(text):
    assert tokenize(text) == []


# --- Retriever -------------------------------------------------------------

CHUNKS = [
    ("tutorial/path-params.md", "Path Parameters",
     "Path parameters let you declare variables in the URL path of an endpoint"),
    ("tutorial/query-params.md", "Query Parameters",
     "Query parameters are key value pairs after the question mark in a URL"),
    ("tutorial/dependencies.md", "Dependencies",
     "Dependency injection with Depends lets you share logic between endpoints"),
    ("advanced/response-headers.md", "Response Headers",
     "Response headers can be set using the Response object in an endpoint"),
    ("tutorial/cors.md", "CORS",
     "CORS middleware allows browsers to call your API from other origins"),
    ("tutorial/background-tasks.md", "Background Tasks",
     "Background tasks run after returning a response to the client"),
    ("tutorial/security.md", "Security",
     "OAuth2 with password flow and bearer tokens secures your endpoints"),
    ("tutorial/testing.md", "Testing",
     "Testing uses TestClient to send requests to your application"),
]


@pytest.fixture
def retriever(tmp_path):
    path = tmp_path / "chunks.json"
    path.write_text(
        json.dumps([
            {"source": source, "heading": heading, "text": text}
            for source, heading, text in CHUNKS
        ]),
        encoding="utf-8",
    )
    return Retriever(str(path))


def test_most_relevant_chunk_is_ranked_first(retriever):
    results = retriever.search("path parameters")
    assert results[0]["source"] == "tutorial/path-params.md"


def test_result_has_expected_fields(retriever):
    result = retriever.search("cors")[0]
    assert set(result) == {"text", "source", "heading", "score"}
    assert result["heading"] == "CORS"
    assert result["score"] > 0


def test_results_are_sorted_by_score_descending(retriever):
    results = retriever.search("cors background testing", k=5)
    scores = [r["score"] for r in results]
    assert len(scores) == 3
    assert scores == sorted(scores, reverse=True)


def test_k_limits_number_of_results(retriever):
    assert len(retriever.search("cors background testing", k=2)) == 2
    assert len(retriever.search("cors background testing", k=10)) == 3


@pytest.mark.parametrize("query", ["", "how do I", "?!"])
def test_empty_or_stopword_only_query_returns_nothing(retriever, query):
    assert retriever.search(query) == []


@pytest.mark.parametrize("k", [0, -1])
def test_non_positive_k_returns_nothing(retriever, k):
    assert retriever.search("path parameters", k=k) == []


def test_query_with_no_matching_words_returns_nothing(retriever):
    assert retriever.search("kubernetes") == []


def test_min_score_filters_weak_matches(retriever, monkeypatch):
    assert retriever.search("path parameters")  # sanity: matches by default
    monkeypatch.setattr(retrieve, "MIN_SCORE", 1000.0)
    assert retriever.search("path parameters") == []


def test_missing_heading_defaults_to_empty_string(tmp_path):
    path = tmp_path / "chunks.json"
    chunks = [
        {"source": f"doc{i}.md", "text": text}
        for i, (_, _, text) in enumerate(CHUNKS)
    ]
    path.write_text(json.dumps(chunks), encoding="utf-8")

    result = Retriever(str(path)).search("cors")[0]

    assert result["heading"] == ""
