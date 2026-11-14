import json
from pathlib import Path


def split_into_sections(text):
    lines = text.split("\n")
    sections = []
    current = []

    for line in lines:
        is_heading = line.startswith("## ") or line.startswith("### ")

        if is_heading and len(current) > 0:
            sections.append("\n".join(current))
            current = []

        current.append(line)

    if len(current) > 0:
        sections.append("\n".join(current))

    return sections


def split_too_long(section, max_chars=1500):
    if len(section) <= max_chars:
        return [section]

    pieces = []
    current = ""
    for para in section.split("\n\n"):
        if current == "":
            current = para
        elif len(current) + len(para) > max_chars:
            pieces.append(current)
            current = para
        else:
            current = current + "\n\n" + para

    if current != "":
        pieces.append(current)
    return pieces


def build_chunks(docs_dir="data/docs"):
    all_chunks = []

    for path in Path(docs_dir).rglob("*.md"):
        # FIX 1a: skip the changelog — hundreds of tiny chunks that game
        # BM25's length boost and outrank real docs
        if path.name == "release-notes.md":
            continue

        # FIX 1b: skip reference stubs — they're just a heading plus an
        # mkdocstrings directive, no real prose to retrieve
        if "reference" in path.parts:
            continue

        text = path.read_text(encoding="utf-8")

        for section in split_into_sections(text):
            for piece in split_too_long(section):
                first_line = piece.split("\n")[0]

                if first_line.startswith("#"):
                    heading = first_line.replace("#", "").strip()
                else:
                    heading = path.stem

                all_chunks.append({
                    "text": piece,
                    "source": str(path.relative_to(docs_dir)),
                    "heading": heading,
                })

    with open("data/chunks.json", "w") as f:
        json.dump(all_chunks, f, indent=2)

    print("made", len(all_chunks), "chunks")


if __name__ == "__main__":
    build_chunks()