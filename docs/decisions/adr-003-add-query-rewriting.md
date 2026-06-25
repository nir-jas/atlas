# ADR 003: Add Query Rewriting Before Retrieval

## Status

Accepted

## Context

User questions may not use the same wording as indexed documents. A single
semantic query can miss relevant chunks when the corpus uses alternate terms or
phrasing.

## Decision

Search the original query plus deterministic rewrites before vector retrieval
results are merged and deduplicated.

## Consequences

- Retrieval recall can improve for differently worded questions.
- Results include `matched_queries` metadata for debugging.
- Each rewrite adds retrieval work and can introduce noise.
- The deterministic provider keeps local behavior testable.

## Alternatives Considered

- Original-query-only retrieval: simpler and faster, but less forgiving.
- LLM-generated rewrites: more flexible, but adds provider cost, latency, and
  nondeterminism before the simpler path is exhausted.
