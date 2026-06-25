# Vector Databases Interview Guide

## Short Explanation

A vector database stores embeddings and supports similarity search over those
vectors.

## Engineer-Level Explanation

Vector search ranks stored vectors by distance from a query vector. In RAG, this
usually means finding document chunks whose embeddings are closest to the
question embedding. A production system also needs metadata filters, predictable
schema design, and observability around ranking quality.

## 2-Minute Interview Answer

Atlas uses PostgreSQL with pgvector so document metadata, chunks, and embeddings
stay in one database. This is a practical early-stage choice: PostgreSQL handles
normal relational data, and pgvector adds vector similarity search without a
separate vector-store service.

## How Atlas Implements This

The vector column is modeled in
`apps/api/src/atlas_api/models/chunk_embedding.py`. Database-side cosine
similarity search is implemented in
`apps/api/src/atlas_api/repositories/retrieval.py`. The pgvector migration is
`migrations/versions/20260622_0004_use_pgvector_embeddings.py`.

## Key Tradeoffs

- PostgreSQL plus pgvector keeps the architecture simple.
- A dedicated vector database may offer more specialized scaling features later.
- Exact search is easier to reason about than approximate search, but may become
  slower as data grows.

## Common Failure Modes

- The pgvector extension is not enabled.
- Stored dimensions do not match query dimensions.
- Metadata filters are applied incorrectly.
- Ranking looks correct by score but the chunks are not useful to the answer.

## Debugging Checklist

- Confirm the database has pgvector enabled.
- Check that embeddings exist for indexed chunks.
- Verify query dimensions match stored dimensions.
- Inspect the SQL-level ranked results.
- Test with and without metadata filters.

## Common Interview Questions

- What does a vector database do?
- Why use pgvector instead of a separate vector database?
- What is cosine similarity?
- How do metadata filters interact with vector search?
- When would approximate nearest neighbor search matter?

## Follow-Up Questions

- How would you scale this beyond a small corpus?
- What indexes would you consider later?
- How would you monitor retrieval latency?
- How would you migrate to another vector store?
