# ADR 004: Add Reranking After Retrieval

## Status

Accepted

## Context

Atlas supports vector, keyword, and hybrid retrieval. Those first-stage ranking
signals are useful but imperfect. Hybrid search in particular combines scores
from different systems, so final order can still need a query-aware relevance
pass.

## Decision

Add a `RerankerService` after retrieval. When enabled, it scores retrieved
chunks against the original user query, sorts by reranker score, applies
`RERANKER_TOP_K`, and filters chunks below `RERANKER_SCORE_THRESHOLD`.

Only a fake reranker provider is supported for now. External reranker APIs are
intentionally out of scope until the service contract and tests are stable.

## Consequences

- Existing vector, keyword, and hybrid search behavior is preserved when
  `RERANKER_ENABLED=false`.
- Search and answer responses expose `reranker_enabled` and `reranker_score`.
- Original retrieval metadata remains visible for debugging.
- Reranking can improve context quality but adds another scoring stage.
- Too strict a threshold can remove all context and trigger no-context answers.

## Alternatives Considered

- Leave retrieval-only ranking: simpler and faster, but weaker for mixed
  vector/keyword result sets.
- Add an external reranker immediately: better realism, but adds cost, latency,
  credentials, and nondeterminism before the local pipeline is proven.
- Fold reranking into retrieval SQL: fewer service classes, but harder to swap
  providers and harder to test independently.
