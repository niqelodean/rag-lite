from retrieve import STOPWORDS

for w in ["work", "need", "want", "how", "the"]:
    print(w, "->", w in STOPWORDS)