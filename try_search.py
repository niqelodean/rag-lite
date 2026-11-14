from retrieve import Retriever

retriever = Retriever()

print()
print("retriever built.", len(retriever.chunks), "chunks loaded.")
print()

questions = [
    "how do path parameters work",
    "what is Depends used for",
    "how do I add a custom response header",
]

for q in questions:
    print("#" * 70)
    print("QUERY:", q)
    print("#" * 70)

    results = retriever.search(q, k=3)
    for n, r in enumerate(results, start=1):
        print()
        print("rank", n, "— score", round(r["score"], 2))
        print("  source: ", r["source"])
        print("  heading:", r["heading"])
        print("  preview:", r["text"][:150].replace("\n", " "))
    print()