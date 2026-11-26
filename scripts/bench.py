import requests, statistics
from ask import SYSTEM, build_context

# (model, extra payload fields)
MODELS = [
    ("llama3.2", {}),
    ("lfm3:1.7b", {}),
]

QUESTIONS = [
    "How do I declare a path parameter?",
    "How do I set a default value for a query parameter?",
    "How do I add a header parameter?",
    "How do I validate a query parameter's max length?",
    "How do I declare a request body?",
]
REPEATS = 2

def get_chunks(q, k=3):
    data = requests.get("http://127.0.0.1:8000/search", params={"q": q, "k": k}).json()
    return data["results"] if isinstance(data, dict) else data

def run(model, extra, prompt):
    r = requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "keep_alive": -1,
        "options": {"temperature": 0.1, "num_ctx": 4096},
        **extra,
    })
    r.raise_for_status()
    return r.json()

def loaded_gb(model):
    ps = requests.get("http://localhost:11434/api/ps").json()
    for m in ps.get("models", []):
        if m["name"].startswith(model):
            return m["size"] / 1e9
    return float("nan")

prompts = [
    "CONTEXT:\n" + build_context(get_chunks(q)) + "\n\nQUESTION: " + q
    for q in QUESTIONS
]

for model, extra in MODELS:
    run(model, extra, prompts[0])  # warm-up, not counted
    tps, totals, tokens, empty = [], [], [], 0
    for p in prompts:
        for _ in range(REPEATS):
            d = run(model, extra, p)
            if not d["message"]["content"].strip():
                empty += 1
            tps.append(d["eval_count"] / d["eval_duration"] * 1e9)
            totals.append(d["total_duration"] / 1e9)
            tokens.append(d["eval_count"])
    print(f"\n{model}  (loaded: {loaded_gb(model):.2f} GB)")
    print(f"  tokens/sec (median): {statistics.median(tps):.1f}")
    print(f"  total time (median): {statistics.median(totals):.2f}s")
    print(f"  output tokens      : {statistics.median(tokens):.0f}")
    print(f"  empty answers      : {empty}/{len(tps)}")