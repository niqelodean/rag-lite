import json
from rank_bm25 import BM25Okapi


# Words that are too common to carry signal. Removed from both chunks and
# queries so matching "how" and "do" stops inflating every chunk's score.
STOPWORDS = {
    "a", "an", "the",
    "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had",
    "i", "you", "we", "they", "he", "she", "it",
    "my", "your", "our", "their", "its",
    "how", "what", "why", "when", "where", "which", "who",
    "this", "that", "these", "those",
    "of", "to", "in", "on", "for", "with", "by", "at", "from", "as",
    "or", "and", "but", "if", "so", "not",
    "can", "could", "would", "should", "will", "may", "might",
    "work", "works", "need", "needs", "want", "wants",
}


def tokenize(text):
    text = text.lower()
    words = []
    current = ""
    for ch in text:
        if ch.isalnum():
            current = current + ch
        else:
            if current != "":
                words.append(current)
                current = ""
    if current != "":
        words.append(current)

    # drop stopwords
    meaningful = []
    for w in words:
        if w not in STOPWORDS:
            meaningful.append(w)
    return meaningful

MIN_SCORE = 1.0

class Retriever:
    def __init__(self, chunks_path="data/chunks.json"):
        with open(chunks_path) as f:
            self.chunks = json.load(f)

        word_lists = []
        for chunk in self.chunks:
            word_lists.append(tokenize(chunk["text"]))

        self.bm25 = BM25Okapi(word_lists)

    def search(self, query, k=3):
        query_words = tokenize(query)
        if not query_words or k <= 0:
            return []

        scores = self.bm25.get_scores(query_words)
        scored = sorted(
            ((float(score), i) for i, score in enumerate(scores)),
            reverse=True,
        )

        results = []
        for score, i in scored:
            if score < MIN_SCORE:
                continue

            chunk = self.chunks[i]
            results.append({
                "text": chunk["text"],
                "source": chunk["source"],
                "heading": chunk.get("heading", ""),
                "score": score,
            })
            if len(results) >= k:
                break

        return results
