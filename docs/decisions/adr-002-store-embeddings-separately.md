# ADR 002: Store Embeddings Separately from Chunks

## Status

Accepted

## Context

Atlas stores document chunks and their embeddings. Chunk text is application
content, while embeddings are model-specific derived data with provider, model,
and dimension metadata.

## Decision

Store embeddings in a separate `chunk_embeddings` table instead of embedding
vectors directly on chunk records.

## Consequences

- Chunk content stays separate from model-derived vector data.
- Provider, model, and dimension metadata can be tracked with each embedding.
- Re-indexing or future multi-embedding support is easier to reason about.
- Queries need a join between chunks, documents, and embeddings.

## Alternatives Considered

- Store vectors directly on chunks: fewer joins, but mixes source content with
  derived model data.
- Store embeddings outside PostgreSQL: more flexible later, but adds an extra
  service now.
