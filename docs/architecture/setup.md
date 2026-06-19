# Setup Instructions

## Backend

```bash
cp .env.example .env
uv sync --extra dev
docker compose up -d postgres
uv run uvicorn atlas_api.main:app --app-dir apps/api/src --reload
```

The API runs on `http://localhost:8000`.

Useful commands:

```bash
uv run pytest
uv run ruff check .
uv run mypy apps/api/src
```

## Database

PostgreSQL runs through Docker Compose:

```bash
docker compose up -d postgres
docker compose logs -f postgres
docker compose down
```

The container uses the `pgvector/pgvector:pg16` image and initializes the
`vector` extension from `scripts/init-db.sql`.

## Frontend

```bash
cd apps/web
npm install
npm run dev
```

The frontend placeholder runs on `http://localhost:3000`.

## Local Files

Store local uploads in `data/uploads/`. Do not commit uploaded files, personal
documents, or secrets.
