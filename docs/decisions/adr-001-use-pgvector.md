# ADR 001: Use PostgreSQL with pgvector for Vector Search

## Status

Accepted

## Context

Atlas needs semantic retrieval over document chunks. The project already uses
PostgreSQL for application data, and the early corpus is small enough that a
separate vector database would add operational complexity before it is needed.

## Decision

Use PostgreSQL with pgvector for vector storage and cosine similarity search.
Keep relational document metadata and vector retrieval in the same database.

## Consequences

- Atlas has one primary database to run locally and in tests.
- Retrieval can combine vector search with relational metadata filters.
- Future scale may require pgvector indexes, tuning, or a separate vector store.

## Alternatives Considered

- Dedicated vector database: more specialized, but premature for the current
  project size.
- In-process vector search: simpler initially, but weaker as a durable backend
  design.
