import requests

SYSTEM = """You answer questions using ONLY the provided context from the FastAPI docs.

Rules:
1. Use only the context below. Do not use outside knowledge.
2. After each factual claim, cite the source like [source: path/to/file.md].
3. If the context does not contain the answer, reply exactly: "Not found in the docs."
4. Keep answers concise: at most.
5 sentences or bullets, plus a short code example if needed.
"""


def build_context(chunks):
    parts = []
    for c in chunks:
        parts.append("[source: " + c["source"] + "]\n" + c["text"])
    return "\n\n---\n\n".join(parts)

def call_llm(prompt):
    r = requests.post("http://localhost:11434/api/chat", json={
        "model": "lfm3:1.7b",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "keep_alive": -1,
        "options": {
            "temperature": 0.1,
            "top_k": 50,
            "repeat_penalty": 1.1,
            "num_ctx": 8192,
        },
    })
    r.raise_for_status()
    d = r.json()
    print("tokens:", d["eval_count"], "| thinking chars:", len(d["message"].get("thinking", "")))
    return d["message"]["content"]


def answer(question, retriever, k=3):
    chunks = retriever.search(question, k)
    if not chunks:
        return {
            "answer": "Not found in the docs.",
            "sources": [],
        }
    context = build_context(chunks)
    prompt = "CONTEXT:\n" + context + "\n\nQUESTION: " + question

    text = call_llm(prompt)

    sources = list(dict.fromkeys(c["source"] for c in chunks))

    return {
        "answer": text,
        "sources": sources,
    }