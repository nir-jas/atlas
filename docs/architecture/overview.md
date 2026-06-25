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

Current locations:

- `apps/api/src/atlas_api/services/knowledge.py`
- `apps/api/src/atlas_api/services/documents.py`
- `apps/api/src/atlas_api/services/retrieval.py`

### Repository Layer

The repository layer hides persistence details behind protocols. Document
indexing and retrieval use PostgreSQL; pgvector performs the production cosine
similarity search in the database, while the in-memory repository remains for
the separate knowledge feature.

Current location:

- `apps/api/src/atlas_api/repositories/base.py`
- `apps/api/src/atlas_api/repositories/memory.py`
- `apps/api/src/atlas_api/repositories/documents.py`
- `apps/api/src/atlas_api/repositories/retrieval.py`

### AI Provider Abstraction

The embedding provider abstraction keeps embedding vendors out of services and
API routes. `fake` is deterministic and the default for tests; `openai` calls
the OpenAI embeddings API when explicitly selected through configuration.

Current location:

- `apps/api/src/atlas_api/ai_providers/base.py`
- `apps/api/src/atlas_api/ai_providers/local.py`
- `apps/api/src/atlas_api/embedding_providers/`

## Data Policy

- No personal documents are committed.
- Runtime uploads belong in `data/uploads/`.
- Uploaded files are ignored by Git.
- Shared examples must be synthetic or public and live under
  `examples/sample_docs/`.

## Growth Path

1. Add learning-note persistence and retrieval evaluation cases under `evals/`.
2. Add a pgvector approximate-nearest-neighbor index once production corpus
   size and query latency justify its maintenance cost.
3. Add additional embedding providers behind the existing embedding-provider
   protocol.
4. Add evaluation cases under `evals/` before changing retrieval or generation
   behavior.
