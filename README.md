# FastAPI Docs RAG

Ask questions about the FastAPI framework and get answers grounded in its official English documentation. FastAPI Docs RAG is a fully local retrieval-augmented generation (RAG) project: it downloads Markdown docs from the FastAPI repository, splits them into heading-aware sections, finds relevant passages with BM25, and sends those passages to a local Ollama model. The API asks the model to cite documentation sources and to respond with `Not found in the docs.` when the retrieved context does not contain an answer.

## Features

- **Local and private:** Retrieval and generation run on your machine using Ollama; no hosted LLM API key or per-request API cost is required. Downloading or refreshing the documentation corpus does require an internet connection.
- **Documentation-grounded answers:** The model receives retrieved FastAPI documentation as its context and is instructed to answer only from that context. This prompt encourages grounding, but generated answers and citations should still be checked against their sources.
- **Source citations:** The answer prompt requests citations in the form `[source: path/to/file.md]`, and the `/ask` response also returns the retrieved source paths.
- **Inspectable retrieval:** The `/search` endpoint exposes the BM25 results, including their text, source, heading, and retrieval score.
- **Rebuildable local data:** Downloaded documents and generated chunks live under `data/`, which is excluded from Git and can be regenerated.

## How It Works

`ingest.py` downloads English Markdown files under `docs/en/docs/` from the official `fastapi/fastapi` GitHub repository. It defaults to the pinned commit `05e6df7e906c3decba377c37548019973f40bf15`; pass `--ref <git-ref-or-sha>` to select another snapshot. `chunk.py` separates content at `##` and `###` headings, then splits long sections at paragraph boundaries. `retrieve.py` tokenizes the resulting passages and ranks them with BM25. When a question reaches the API, the top three matching passages are placed into a prompt and sent to the local Ollama model configured in `ask.py` (default: `llama3.2`).

```text
Official FastAPI Docs
        |
        v
     Ingest  (ingest.py)
        |
        v
      Chunk  (chunk.py)
        |
        v
   BM25 Index  (retrieve.py)
        |
        v
 FastAPI API  (main.py)
        |
        v
 Local LLM via Ollama  (ask.py)
        |
        v
 Answer with source citations
```

The BM25 index is built in memory when the API starts from `data/chunks.json`; the downloaded docs and chunk JSON are stored locally. No vector database is used.

## Requirements

- Python 3.10 or newer
- Git
- Internet access for cloning and downloading the documentation
- [Ollama](https://ollama.com/) installed locally for the `/ask` endpoint

## Getting Started

### 1. Clone the repository and create a virtual environment

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

### 2. Install dependencies

Install the application dependencies:

```bash
pip install fastapi uvicorn requests rank_bm25
```

Alternatively, install the versions recorded in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 3. Download and prepare the documentation

Run both scripts from the repository root:

```bash
python ingest.py
python chunk.py
```

`ingest.py` creates `data/docs/` and downloads the English Markdown documentation from the pinned commit. To intentionally use another upstream revision, pass it explicitly, for example `python ingest.py --ref <commit-sha>`. `chunk.py` reads those files and writes the passages to `data/chunks.json`. The first command needs internet access and uses the GitHub API and raw GitHub content. Both generated data paths are ignored by Git.

### 4. Install and start Ollama

Install Ollama for your operating system, then download the default model:

```bash
ollama pull llama3.2
```

Start the Ollama service in a terminal and leave it running:

```bash
ollama serve
```

The application sends generation requests to `http://localhost:11434/api/generate`. If you change the model or endpoint, update `ask.py` accordingly.

### 5. Start the FastAPI server

In another terminal, activate the virtual environment, move to the repository root, and run:

```bash
uvicorn main:app --reload
```

Visit **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** to test the API interactively. The server expects `data/chunks.json` to exist when it starts, and Ollama must be running to use `/ask`.

## API Endpoints

### `GET /search`

Search the local chunks with BM25. The required `q` parameter is the query string; optional `k` sets the number of results and defaults to `3`.

```bash
curl "http://127.0.0.1:8000/search?q=path+parameters&k=3"
```

Each result includes `text`, `source`, `heading`, and `score`.

### `POST /ask`

Retrieve relevant passages and ask Ollama to answer from that context. The request body accepts a `question` and optional `k` (default `3`).

```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"How do path parameters work?","k":3}'
```

The response contains the generated `answer` and a `sources` array listing the retrieved documentation paths. The prompt instructs the model to cite factual claims and return `Not found in the docs.` when the context does not answer the question. As with any generative model, prompt instructions cannot guarantee perfect compliance; verify important answers against the cited documentation.

## Project Structure

```text
rag-lite/
├── ask.py                # Builds context and calls the local Ollama API
├── chunk.py              # Splits downloaded Markdown into sections and chunks
├── ingest.py             # Downloads official FastAPI English documentation
├── main.py               # FastAPI application and API endpoints
├── retrieve.py           # Tokenization and BM25 search
├── index.html            # Simple web frontend served at /
├── eval/                 # Ground-truth questions, validation, and eval baseline
├── scripts/              # Debugging helpers (inspect chunks, try searches)
├── tests/                # pytest suite for chunking, retrieval, and evaluation
├── requirements.txt      # Pinned Python dependencies
├── requirements-dev.txt  # Adds test dependencies (pytest)
└── data/                 # Generated locally; excluded from Git
    ├── docs/             # Downloaded Markdown source files
    └── chunks.json       # Chunk records used by retrieval
```

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests cover chunking, BM25 retrieval, and evaluation scoring using small in-memory fixtures, so they need no downloaded docs, internet access, or Ollama. To check the question set against your local indexed corpus, run `python eval/check_questions.py` after ingestion.

## Future Improvements

- Replace or complement BM25 with vector embeddings and [ChromaDB](https://www.trychroma.com/) to improve retrieval when users phrase queries with synonyms that do not share exact keywords with the docs.
- Add configurable model, Ollama endpoint, and retrieval settings.
- Extend automated checks to ingestion and citation coverage, and run the retrieval evaluation in CI.

## Evaluation

The retrieval harness evaluates 50 questions from `eval/questions.json`: 42 answerable questions and 8 questions that should be refused. Run the checks from the repository root:

```bash
python eval/check_questions.py
python eval/runeval.py
```

The checker validates answerable evidence terms within individual indexed chunks, flags overly common evidence terms, checks refusal topic terms against the documentation chunks, and validates question category and verification metadata. `verified` remains false until a person checks the question and its labels; when setting it true, fill in `verified_by` and an ISO-8601 `verified_at` value.

Baseline BM25 results at `k=5` and `MIN_SCORE=1.0`:

- **Hit @ 1:** 0.52
- **Hit @ 3:** 0.79
- **Hit @ 5:** 0.81
- **MRR:** 0.64
- **Recall @ 5:** 0.71
- **Evidence @ 5:** 0.69

Refusal questions are reported separately with each raw top score and the raw minimum, median, and maximum. Raw scores are measured before `MIN_SCORE`; they indicate retrieval strength, not whether the generated answer actually refuses. The baseline records hashes for the local documentation and chunk snapshot. The upstream commit for that existing snapshot was not recorded, so its origin cannot be reconstructed from the old baseline; future ingests use the pinned commit above.

*Known limitation: BM25 struggles with synonyms (e.g., searching "add header" vs. "set header").*

## License

This project is licensed under the [MIT License](LICENSE). The FastAPI documentation fetched by the ingestion script remains subject to its own licensing terms.
