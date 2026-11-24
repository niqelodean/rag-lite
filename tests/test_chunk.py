import json
from pathlib import Path

from chunk import build_chunks, split_into_sections, split_too_long


# --- split_into_sections ---------------------------------------------------

def test_splits_on_h2_and_h3_headings():
    text = "## One\nbody one\n### Two\nbody two"
    sections = split_into_sections(text)
    assert sections == ["## One\nbody one", "### Two\nbody two"]


def test_does_not_split_on_h1_or_h4():
    text = "## One\n# not a split\n#### also not a split\nbody"
    sections = split_into_sections(text)
    assert len(sections) == 1


def test_keeps_text_before_first_heading_as_its_own_section():
    text = "intro line\n\n## First\nbody"
    sections = split_into_sections(text)
    assert len(sections) == 2
    assert sections[0].startswith("intro line")
    assert sections[1].startswith("## First")


def test_empty_text_gives_single_empty_section():
    assert split_into_sections("") == [""]


# --- split_too_long --------------------------------------------------------

def test_short_section_is_returned_unchanged():
    assert split_too_long("short text", max_chars=100) == ["short text"]


def test_long_section_splits_on_paragraph_boundaries():
    para = "x" * 40
    section = "\n\n".join([para] * 10)

    pieces = split_too_long(section, max_chars=100)

    assert len(pieces) > 1
    assert all(len(p) <= 100 for p in pieces)
    # No text is lost or reordered: pieces rejoin into the original section.
    assert "\n\n".join(pieces) == section


def test_single_oversized_paragraph_is_kept_whole():
    para = "y" * 300
    assert split_too_long(para, max_chars=100) == [para]


# --- build_chunks ----------------------------------------------------------

def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_build_chunks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    build_chunks("data/docs")
    with open(tmp_path / "data" / "chunks.json", encoding="utf-8") as f:
        return json.load(f)


def test_build_chunks_sets_source_and_heading(tmp_path, monkeypatch):
    docs = tmp_path / "data" / "docs"
    _write(
        docs / "tutorial" / "path-params.md",
        "Intro text\n\n## Path Parameters\n\nSome text\n\n### Types\n\nMore text\n",
    )

    chunks = _run_build_chunks(tmp_path, monkeypatch)

    assert {c["source"] for c in chunks} == {"tutorial/path-params.md"}
    # Text before the first heading falls back to the file name as its heading.
    assert [c["heading"] for c in chunks] == ["path-params", "Path Parameters", "Types"]
    assert all(set(c) == {"text", "source", "heading"} for c in chunks)


def test_build_chunks_skips_release_notes_and_reference_stubs(tmp_path, monkeypatch):
    docs = tmp_path / "data" / "docs"
    _write(docs / "tutorial" / "keep.md", "## Keep me\n\nreal prose\n")
    _write(docs / "release-notes.md", "## 1.0.0\n\nchangelog entry\n")
    _write(docs / "reference" / "fastapi.md", "## FastAPI\n\n::: fastapi.FastAPI\n")

    chunks = _run_build_chunks(tmp_path, monkeypatch)

    assert {c["source"] for c in chunks} == {"tutorial/keep.md"}


def test_build_chunks_splits_long_sections(tmp_path, monkeypatch):
    docs = tmp_path / "data" / "docs"
    long_body = "\n\n".join(["word " * 100] * 10)  # well over 1500 chars
    _write(docs / "big.md", "## Big\n\n" + long_body + "\n")

    chunks = _run_build_chunks(tmp_path, monkeypatch)

    assert len(chunks) > 1
    assert all(c["source"] == "big.md" for c in chunks)
