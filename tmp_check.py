 # tmp_check.py  (delete after)
from retrieve import Retriever

r = Retriever()
for q in [
    "How do I add a custom response header?",
    "How do I test FastAPI applications?",
    "How do I read a request header in a route?",
    "How do I declare a query parameter with an integer type?",
]:
    print(f"\n{'='*60}\n{q}\n{'='*60}")
    for h in r.search(q, k=3):
        print(f"  {h['source']:<45} score={h['score']:.2f}")