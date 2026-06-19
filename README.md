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

## License

MIT. See `LICENSE`.
