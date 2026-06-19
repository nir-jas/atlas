# Atlas Architecture

Atlas is organized as a small monorepo with a clean backend boundary and a
placeholder frontend that can be expanded independently.

## System Context

```text
Browser
  |
  v
Next.js app
  |
  v
FastAPI API
  |
  +--> Service layer
  |      |
  |      +--> Repository layer
  |      |      |
  |      |      +--> PostgreSQL + pgvector
  |      |
  |      +--> AI provider abstraction
  |             |
  |             +--> Local provider now, external model providers later
```

## Backend Layers

### HTTP Layer

The HTTP layer owns routing, request validation, response models, and status
codes. It should not contain database queries or model-provider logic.

Current location:

- `apps/api/src/atlas_api/http/router.py`
- `apps/api/src/atlas_api/http/system.py`
- `apps/api/src/atlas_api/http/v1/`

Routes are grouped by transport and API version. The application includes
`/api/v1` once from `http/router.py`; individual route modules define only their
domain paths such as `/notes` and `/answers`.

This follows the same broad pattern used in larger FastAPI applications:
feature-specific routers stay small, common prefixes and tags are declared on
routers or `include_router()`, and the app entrypoint only composes routers.

### Service Layer

The service layer owns application behavior. It coordinates repositories and AI
providers, keeps use cases testable, and avoids framework-specific code.

Current location:

- `apps/api/src/atlas_api/services/knowledge.py`

### Repository Layer

The repository layer hides persistence details behind protocols. The current
scaffold uses an in-memory repository for a runnable first version. PostgreSQL
and pgvector are available through Docker Compose for the real implementation.

Current location:

- `apps/api/src/atlas_api/repositories/base.py`
- `apps/api/src/atlas_api/repositories/memory.py`

### AI Provider Abstraction

The AI provider abstraction keeps model vendors out of services and API routes.
The local provider returns deterministic responses for development and tests.

Current location:

- `apps/api/src/atlas_api/ai_providers/base.py`
- `apps/api/src/atlas_api/ai_providers/local.py`

## Data Policy

- No personal documents are committed.
- Runtime uploads belong in `data/uploads/`.
- Uploaded files are ignored by Git.
- Shared examples must be synthetic or public and live under
  `examples/sample_docs/`.

## Growth Path

1. Add SQLAlchemy models and migrations for documents, chunks, embeddings, and
   learning notes.
2. Implement a PostgreSQL repository using pgvector similarity search.
3. Add external AI providers behind the existing `AIProvider` protocol.
4. Add evaluation cases under `evals/` before changing retrieval or generation
   behavior.
