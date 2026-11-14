import requests

SYSTEM = """You answer questions using ONLY the provided context from the FastAPI docs.

Rules:
1. Use only the context below. Do not use outside knowledge.
2. After each factual claim, cite the source like [source: path/to/file.md].
3. If the context does not contain the answer, reply exactly: "Not found in the docs."
"""


def build_context(chunks):
    parts = []
    for c in chunks:
        parts.append("[source: " + c["source"] + "]\n" + c["text"])
    return "\n\n---\n\n".join(parts)


# --- Option A: Ollama (local) ---
def call_llm(prompt):
    r = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3.2",
        "system": SYSTEM,
        "prompt": prompt,
        "stream": False,
    })
    r.raise_for_status()
    return r.json()["response"]


def answer(question, retriever, k=3):
    chunks = retriever.search(question, k)
    context = build_context(chunks)
    prompt = "CONTEXT:\n" + context + "\n\nQUESTION: " + question

    text = call_llm(prompt)

    sources = []
    for c in chunks:
        sources.append(c["source"])

    return {
        "answer": text,
        "sources": sources,
    }