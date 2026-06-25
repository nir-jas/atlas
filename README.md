# Atlas

Atlas is an open-source personal knowledge platform for learning AI Engineering.
It starts as a small monorepo with a FastAPI backend, a Next.js frontend
placeholder, PostgreSQL with pgvector through Docker Compose, and a testable
Python service structure.

The repository intentionally contains no personal documents. Runtime uploads go
under `data/uploads/`, and uploaded files are ignored by Git.

## Repository Layout

```text
apps/
  api/                 FastAPI backend
  web/                 Next.js frontend placeholder
docs/
  architecture/        Architecture and setup notes
  learning-notes/      Notes created while learning AI Engineering
evals/                 Evaluation fixtures, prompts, and experiments
examples/
  sample_docs/         Public sample documents only
scripts/               Local helper scripts
data/
  uploads/             Local upload storage, ignored by Git
```

## Prerequisites

- Python 3.11 or newer
- uv
- Docker and Docker Compose
- Node.js 20 or newer for the frontend placeholder

Install uv if needed:

```bash
brew install uv
```

or:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

1. Create your local environment file:

   ```bash
   cp .env.example .env
   ```

2. Install Python dependencies:

   ```bash
   uv sync --extra dev
   ```

3. Start PostgreSQL with pgvector:

   ```bash
   docker compose up -d postgres
   ```

4. Apply database migrations:

   ```bash
   uv run alembic upgrade head
   ```

5. Run the API:

   ```bash
   uv run uvicorn atlas_api.main:app --app-dir apps/api/src --reload
   ```

6. Check the health endpoint:

   ```bash
   curl http://localhost:8000/health
   ```

7. Try the versioned API:

   ```bash
   curl http://localhost:8000/api/v1/notes
   ```

8. Run tests:

   ```bash
   uv run pytest
   ```

## Embeddings and Retrieval

Atlas defaults to deterministic fake embeddings so local development and tests
never make network calls. To use OpenAI embeddings, set these values in `.env`
and re-index the documents whose embeddings should use the configured model:

```dotenv
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_api_key
EMBEDDING_MODEL=text-embedding-3-small
VECTOR_DIMENSIONS=1536
```

`VECTOR_DIMENSIONS` must match the output size requested from the embedding
model. The OpenAI `text-embedding-3-small` default is 1536. `/rag/search`
embeds the query and asks PostgreSQL with pgvector to rank matching chunks when
`search_mode` is `vector` or `hybrid`.

Retrieval expands each request with deterministic query rewrites before search.
The original query is always searched first, followed by fake-provider rewrites
in local development and tests. Atlas searches every query, merges the results,
deduplicates by `chunk_id`, keeps the highest similarity score for each chunk,
and returns `matched_queries` metadata showing which queries retrieved it.

`/rag/search` and `/rag/answer` accept `search_mode` values of `vector`,
`keyword`, and `hybrid`; `hybrid` is the default. Keyword search runs over chunk
text and uses PostgreSQL full-text search in PostgreSQL-backed environments,
with a small SQLite fallback for local tests. Hybrid search runs vector and
keyword search independently, merges the result sets, deduplicates by
`chunk_id`, and ranks with reciprocal rank fusion: each source contributes
`1 / (60 + rank)` and chunks found by both sources move up. Results preserve
`source_name`, `collection`, `section`, `chunk_index`, `similarity_score`,
`keyword_rank`, and `matched_by` metadata.

Reranking is an optional second pass after retrieval. When enabled, Atlas first
fetches `top_k` candidates with the selected search mode, scores each chunk
against the original user query, sorts by `reranker_score`, keeps up to
`RERANKER_TOP_K`, and removes chunks below `RERANKER_SCORE_THRESHOLD`. The fake
provider is deterministic and local; no external reranker APIs are configured
yet.

```dotenv
RERANKER_ENABLED=false
RERANKER_PROVIDER=fake
RERANKER_TOP_K=5
RERANKER_SCORE_THRESHOLD=0.80
```

To run PostgreSQL integration coverage, point `ATLAS_TEST_DATABASE_URL` at an
isolated pgvector-enabled test database. It uses the fake provider and does not
call OpenAI:

```bash
ATLAS_TEST_DATABASE_URL=postgresql+psycopg://atlas:atlas_dev_password@localhost:5432/atlas_test \
  uv run pytest -m integration
```

## Context Preview

`POST /api/v1/rag/context-preview` shows the exact context that a later answer
generation step would receive. It performs retrieval and context assembly only;
it does not call an LLM.

```json
{
  "query": "How does retrieval work?",
  "top_k": 5,
  "max_chunks": 3,
  "similarity_score_threshold": 0.7
}
```

The response preserves retrieval rank and includes source and section metadata
for each assembled chunk. `max_chunks` bounds prompt size after retrieval. A
`similarity_score_threshold` excludes chunks below the supplied cosine
similarity score. Higher thresholds reduce irrelevant context but can remove
useful supporting detail; lower thresholds preserve recall but consume more of
the eventual model context window. Keeping this assembly step separate makes
the prompt inspectable before an LLM is introduced.

## Answer Generation

`POST /api/v1/rag/answer` retrieves matching chunks, filters out scores below
`similarity_score_threshold` (or `ANSWER_SIMILARITY_SCORE_THRESHOLD`), retains
the highest-ranked chunks that fit `ANSWER_CONTEXT_MAX_CHARACTERS`, assembles
their context, and generates an answer. Citations are generated from the exact
selected chunks and returned separately from the answer text. The response also
returns the selected `retrieved_chunks` so retrieval, keyword, and reranker
metadata can be inspected.

```json
{
  "query": "How does retrieval work?",
  "top_k": 5,
  "collection": "learning"
}
```

`LLM_PROVIDER=fake` is the default and produces deterministic local answers.
Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY` to use the OpenAI provider;
`LLM_MODEL` selects the model. The provider receives an instruction to answer
only from the assembled context, while Atlas itself owns citations so source
metadata is not mixed into the answer text.

If retrieval produces no chunks that meet the score threshold or fit the
context budget, Atlas returns `Insufficient context to answer the question.`
with an empty citation list and does not call the LLM. Provider call failures
return HTTP 502 rather than a fabricated answer.

## RAG Evals

Atlas includes a small public-safe RAG evaluation fixture at
`evals/rag_cases.json`. Run it with fake providers from the repository root:

```bash
uv run python scripts/run_rag_evals.py
```

The harness creates an isolated in-memory app, seeds synthetic documents, calls
`/api/v1/rag/answer`, checks expected cited sources and answer phrases, verifies
no-context handling, and prints per-case pass/fail plus a final score. It does
not call OpenAI by default.

## Frontend Placeholder

The frontend is intentionally minimal:

```bash
cd apps/web
npm install
npm run dev
```

Then open `http://localhost:3000`.

## Development Notes

- Keep personal notes, PDFs, and uploaded files out of the repository.
- Add only sanitized examples under `examples/sample_docs/`.
- Keep `/api/v1` in the router aggregator, not in individual route handlers.
- Put backend HTTP handlers in the HTTP layer, business logic in services, data
  access behind repositories, and model-provider calls behind provider
  abstractions.
- Add migrations before using PostgreSQL for production data.
- Plain text, Markdown, and PDFs with extractable text are chunked and indexed.
  Other file types are stored as uploaded documents until an extractor exists.

## License

MIT. See `LICENSE`.
