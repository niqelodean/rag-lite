# FastAPI Docs RAG

A small retrieval-augmented generation app for asking questions about the FastAPI documentation. It downloads the official English Markdown docs, splits them into chunks, ranks passages with BM25, and can send the retrieved passages to a local Ollama model.

The FastAPI server and model run locally. The browser UI loads the Marked.js Markdown renderer from jsDelivr, so the UI needs internet access to render formatted answers. Ingestion also needs internet access to download docs.

## What it does

1. `ingest.py` downloads Markdown under `docs/en/docs/` from the FastAPI repository. The default is pinned to commit `05e6df7e906c3decba377c37548019973f40bf15`; pass `--ref <git-ref-or-sha>` to choose another revision.
2. `chunk.py` splits documents at `##` and `###` headings and breaks long sections at paragraph boundaries. It skips release notes and `reference/` stubs.
3. `retrieve.py` builds an in-memory BM25 index from `data/chunks.json`, removes common stopwords, and returns up to `k` passages with scores at or above `MIN_SCORE` (currently `1.0`).
4. `/ask` sends the retrieved passages to Ollama (`llama3.2` by default). The prompt asks the model to answer from those passages and cite their source paths.

If retrieval returns no passages, `/ask` returns `Not found in the docs.` with an empty source list. When passages are found, the model is prompted to use the supplied context; this instruction does not guarantee answer accuracy or valid citations.

## Requirements

- Python 3.10 or newer
- Internet access to download the documentation; the browser UI also loads Marked.js from jsDelivr
- [Ollama](https://ollama.com/) and the `llama3.2` model for `/ask`

Git is needed for the clone step below. The `/search` endpoint can be used without Ollama.

## Setup

Clone the project and create an environment:

```bash
git clone https://github.com/niqelodean/rag-lite.git
cd rag-lite
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the pinned project dependencies and prepare the corpus:

```bash
pip install -r requirements.txt
python ingest.py
python chunk.py
```

To use a different FastAPI revision, run `python ingest.py --ref <commit-sha>`. If changing revisions after a prior ingest, remove `data/docs/` first so files removed upstream do not remain in the corpus, then rerun `ingest.py` and `chunk.py`.

`data/docs/` and `data/chunks.json` are generated locally and ignored by Git. The server loads `data/chunks.json` when it starts, so ingest and chunk the docs before launching it.

Install and start Ollama in another terminal:

```bash
ollama pull llama3.2
ollama serve
```

Start the app from the project root:

```bash
uvicorn main:app --reload
```

Open the UI at [http://127.0.0.1:8000/](http://127.0.0.1:8000/) or the interactive API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). The Ollama API URL and model are set in `ask.py`.

## API

### `GET /search`

Searches the local BM25 index. `q` is required; `k` is optional and defaults to `3`. Results include the passage text, source path, heading, and score. A query may return fewer than `k` results if too few passages meet `MIN_SCORE`.

```bash
curl "http://127.0.0.1:8000/search?q=path+parameters&k=3"
```

### `POST /ask`

Retrieves passages and asks Ollama to answer from them. The request accepts a `question` and optional `k` (default `3`). The response contains `answer` and `sources`.

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"How do path parameters work?","k":3}'
```

If no passages are retrieved, the app returns `{"answer":"Not found in the docs.","sources":[]}` without calling Ollama. Otherwise, it returns the model response and the source paths for the passages provided as context.

## Evaluation and tests

The retrieval evaluation uses 50 questions in `eval/questions.json`: 42 answerable questions and 8 intended refusal questions. From the project root, validate the question set against the local chunks and run the evaluation:

```bash
python eval/check_questions.py
python eval/runeval.py
```

The checker confirms expected sources are indexed, each evidence term appears in at least one expected-source chunk (multi-word terms must be contiguous phrases), evidence terms are not overly generic, and refusal topic terms are absent from documentation chunks. It also checks categories and verification metadata. Questions are currently marked unverified; only set `verified` to true after a person reviews the question and labels, and then provide `verified_by` and an ISO-8601 `verified_at` timestamp.

The stored retrieval baseline at `k=5` and `MIN_SCORE=1.0` is:

| Metric | Score |
| --- | ---: |
| Hit @ 1 | 0.52 |
| Hit @ 3 | 0.79 |
| Hit @ 5 | 0.81 |
| MRR | 0.64 |
| Recall @ 5 | 0.71 |
| Evidence @ 5 | 0.69 |

Refusal queries are reported separately with each raw top score and the raw minimum, median, and maximum, before `MIN_SCORE` filtering. These metrics measure retrieval only; they do not measure generated answer quality, citation accuracy, or actual refusal behavior.

The existing baseline records hashes of its local docs and chunk files, but its original upstream FastAPI commit was not recorded. Therefore, its scores cannot be attributed to the currently pinned docs revision. To create a comparable baseline for the pinned revision, ingest and chunk that corpus, run the checker and evaluation, then update `eval/baseline-v1.txt` with the results and new data hashes.

Run the test suite with:

```bash
pip install -r requirements-dev.txt
pytest
```

The tests use small fixtures and do not require downloaded docs, internet access, or Ollama.

## Project files

```text
rag-lite/
├── ask.py                  # Ollama prompt and answer generation
├── chunk.py                # Markdown section and chunk splitting
├── index.html              # Browser UI
├── ingest.py               # Pinned FastAPI docs downloader
├── main.py                 # FastAPI app and routes
├── retrieve.py             # Tokenization and BM25 search
├── eval/
│   ├── questions.json      # Evaluation question set
│   ├── check_questions.py  # Question/corpus validation
│   ├── runeval.py          # Retrieval evaluation
│   └── baseline-v1.txt     # Recorded results and corpus fingerprints
├── scripts/                # Search and corpus inspection helpers
├── tests/                  # Chunking, retrieval, and evaluation tests
├── requirements.txt
├── requirements-dev.txt
└── data/                   # Generated locally; ignored by Git
    ├── docs/
    └── chunks.json
```

## License

This project is licensed under the [MIT License](LICENSE). The downloaded FastAPI documentation remains subject to its own licensing terms.
