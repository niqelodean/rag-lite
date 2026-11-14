import json

chunks = json.load(open("data/chunks.json"))
print("total chunks:", len(chunks))
print()

# show 3 chunks picked from the middle, where real content lives
start = len(chunks) // 2
for c in chunks[start:start + 3]:
    print("=" * 70)
    print("source:  ", c["source"])
    print("heading: ", c["heading"])
    print("length:  ", len(c["text"]), "chars")
    print("-" * 70)
    print(c["text"][:500])
    print()